# src/plugins/help/_services.py
"""帮助服务

- 按插件清单与实例启用集聚合菜单数据源
- 提供单命令解析与图片渲染
"""

import hashlib
import threading
from pathlib import Path
from typing import TypeAlias

from PIL import Image, ImageDraw, ImageFont

from core.domain import CommandFlag, PluginFileName
from core.dto import HelpCommandDTO
from system.profile_env import ASSET_FONT_NAME, ASSETS_DIR
from utils import get_logger
from utils.paths import HELP_IMAGE, PROFILE_DIR
from utils.plugin import enabled_manifests

from .._shared.messages import BotMessage

# 菜单行三元组：行类型、行文本、命令清单项（非命令行留空）
_MenuRow: TypeAlias = tuple[str, str, HelpCommandDTO | None]

# 菜单条目三元组：行类型、左列文本、右列说明
_MenuEntry: TypeAlias = tuple[str, str, str]

# 帮助图属实例产物，落实例数据目录，随实例隔离不共用
_SAVE_PATH = HELP_IMAGE

# 指纹与图片同目录成对落盘，任一缺失即视为缓存未命中
_DIGEST_PATH = HELP_IMAGE.with_suffix(".digest")
_RENDER_LOCK = threading.Lock()
_FONT_PATH = ASSETS_DIR / ASSET_FONT_NAME  # 字体是全局资源，不随实例复制
_logger = get_logger("Plg.Help")


class _HelpRenderConfig:
    """帮助菜单图片渲染配置"""

    font_size: int = 30
    line_spacing: int = 10  # 行间距
    padding: int = 15  # 画布边距
    cmd_desc_gap: int = 20  # 命令与描述间距
    flag_indent: int = 4  # 开关行缩进字符数
    color_mode: str = "RGB"  # PIL 色彩模式
    bg_color: str = "#FFFFFF"  # 背景色
    text_color: str = "#000000"  # 文字颜色


# 帮助图首尾两段全局说明，不挂任何插件
_MENU_HEAD: list[_MenuRow] = [
    ("section", "Fool 的功能列表", None),
    (
        "note",
        "注：所有命令可带 -h 查看可用输入，请不要删除机器人发出的提示消息",
        None,
    ),
]
_MENU_TAIL: list[_MenuRow] = [("section", "未完待续", None)]


def _build_menu_data() -> list[_MenuRow]:
    """聚合帮助菜单数据源

    - 插件段按启用序列拼接，与路由注册同序
    - 空 section 或 note 省略对应行
    - 命令行带上清单原条目
    """
    rows: list[_MenuRow] = [*_MENU_HEAD]
    for manifest in enabled_manifests(PROFILE_DIR / PluginFileName.STATE):
        for section in manifest.help_section:
            if section.section:
                rows.append(("section", section.section, None))
            if section.note:
                rows.append(("note", section.note, None))
            for command in section.commands:
                rows.append(("command", command.cmd, command))
    rows.extend(_MENU_TAIL)
    return rows


_HELP = _HelpRenderConfig()


def _build_help_menu() -> tuple[
    dict[str, str], dict[str, HelpCommandDTO], list[_MenuEntry]
]:
    """构建帮助菜单数据

    - 登记的开关每个单占一条，紧跟所属命令条目
    """
    help_list: dict[str, str] = {}
    command_specs: dict[str, HelpCommandDTO] = {}
    display_order: list[_MenuEntry] = []

    for item_type, content, command in _build_menu_data():
        if command is None:
            display_order.append((item_type, content, ""))
            continue
        help_list[command.cmd] = command.desc
        command_specs[command.cmd] = command
        display_order.append(("command", command.cmd, command.desc))
        display_order.extend(("flag", flag, note) for flag, note in command.flags)

    return help_list, command_specs, display_order


help_list, command_specs, _display_order = _build_help_menu()


def _menu_digest() -> str:
    """计算菜单内容指纹

    - 启用集与帮助文案全量参与，行序影响摘要
    """
    lines = [f"{item_type}|{label}|{note}" for item_type, label, note in _display_order]
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def _cache_hit(digest: str) -> bool:
    """判断帮助图缓存是否命中

    - 图片与指纹文件同在且内容一致才算命中
    """
    if not _SAVE_PATH.is_file() or not _DIGEST_PATH.is_file():
        return False
    try:
        return _DIGEST_PATH.read_text(encoding="utf-8").strip() == digest
    except OSError:
        return False


def resolve_single_help(name: str) -> str:
    """取单命令帮助文案

    - 命令名取自入站事件的命令载体
    - 清单登记的可用输入追加在描述下一行
    """
    desc = help_list.get(name)
    if desc is None:
        return BotMessage.CMD_FORMAT_ERROR
    spec = command_specs.get(name)
    if spec is None:
        return desc
    return f"{desc}\n{_usage_line(spec)}"


def _usage_line(spec: HelpCommandDTO) -> str:
    """拼单命令的可用输入行

    - -h 全命令默认支持，清单 flag 追加其后
    - 开关说明只进帮助图，这一行只列开关
    """
    inputs = [CommandFlag.HELP, *(flag for flag, _ in spec.flags)]
    return BotMessage.CMD_USAGE.format(inputs="、".join(inputs))


def prewarm() -> None:
    """启动前按菜单指纹决定是否重画帮助图

    - 指纹相同即复用现图
    - 重画失败不阻断，首次请求时补画
    """
    digest = _menu_digest()
    try:
        with _RENDER_LOCK:
            if _cache_hit(digest):
                _logger.debug("帮助菜单未变，复用缓存图片")
                return
            _render_menu(digest)
        _logger.debug("帮助菜单图片已刷新")
    except Exception as e:
        _logger.send_error("帮助菜单预热失败，首次请求时重试", e)


def generate_image() -> Path:
    """获取帮助菜单图片

    - 双重检查加锁，保证只绘制一次
    """
    digest = _menu_digest()
    if _cache_hit(digest):
        return _SAVE_PATH
    with _RENDER_LOCK:
        if _cache_hit(digest):
            return _SAVE_PATH
        return _render_menu(digest)


def _entry_line(entry: _MenuEntry) -> str:
    """把菜单条目拼成一行文本

    - 命令与开关各占左列，说明同列对齐
    - 段名与备注整行是文本，无左列
    """
    item_type, label, note = entry
    if item_type == "command":
        prefix = f"/{label}"
    elif item_type == "flag":
        prefix = f"{'':<{_HELP.flag_indent}}{label}"
    else:
        return label
    return f"{prefix:<{_HELP.cmd_desc_gap}}{note}"


def _render_menu(digest: str) -> Path:
    """绘制菜单图片并写指纹文件

    - 仅缓存未命中时调用
    """
    # 使用字体对象获取真实的像素宽度
    font = ImageFont.truetype(_FONT_PATH, _HELP.font_size)

    # 预计算所有行的文本和最大宽度
    lines: list[str] = []
    max_width: float = 0.0

    for entry in _display_order:
        line = _entry_line(entry)
        lines.append(line)
        max_width = max(max_width, font.getlength(line))

    # 创建画布并绘制
    line_height = _HELP.line_spacing + _HELP.font_size
    padding = _HELP.padding
    img_width = int(max_width) + padding * 2
    img_height = len(lines) * line_height + padding * 2
    img = Image.new(_HELP.color_mode, (img_width, img_height), _HELP.bg_color)
    dr = ImageDraw.Draw(img)

    for i, line in enumerate(lines):
        dr.text(
            (padding, padding + i * line_height), line, font=font, fill=_HELP.text_color
        )

    # 图与指纹成对落盘，缺一即判缓存未命中
    _SAVE_PATH.parent.mkdir(parents=True, exist_ok=True)
    img.save(_SAVE_PATH)
    _DIGEST_PATH.write_text(digest, encoding="utf-8")
    return _SAVE_PATH
