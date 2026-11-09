# src/bundled/help/_services.py
"""帮助服务

- 按插件清单与实例启用集聚合菜单数据源
- 单命令解析与图片渲染
"""

import hashlib
import threading
from pathlib import Path
from typing import TypeAlias

from PIL import Image, ImageDraw, ImageFont

from finshin_sdk.domain import CommandFlag, CommandRole, PluginFileName
from finshin_sdk.dto import HelpCommandDTO, HelpFlagDTO
from system.profile_env import ASSET_FONT_NAME, ASSETS_DIR
from utils import get_logger
from utils.paths import HELP_IMAGE, PROFILE_DIR
from utils.plugin import enabled_manifests

from .._shared.messages import BotMessage

# 菜单行三元组：行类型、行文本、命令清单项（非命令行留空）
_MenuRow: TypeAlias = tuple[str, str, HelpCommandDTO | None]

# 菜单条目三元组：行类型、左列文本、右列说明
_MenuEntry: TypeAlias = tuple[str, str, str]

# 段与段之间的空行，只撑开留白，不参与文字宽度
_MENU_GAP: _MenuRow = ("gap", "", None)

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
    line_spacing: int = 18  # 行间距
    padding: int = 15  # 画布边距
    column_gap: int = 60  # 左列与说明列的像素间距
    flag_indent: int = 4  # 开关行缩进字符数
    color_mode: str = "RGB"  # PIL 色彩模式
    bg_color: str = "#FFFFFF"  # 背景色
    text_color: str = "#000000"  # 文字颜色


# 帮助图首尾两段全局说明，不挂任何插件
_MENU_HEAD: list[_MenuRow] = [
    ("section", "Finshin Impact 功能列表", None),
    (
        "note",
        "注：所有命令可带 -h 查看可用输入，请不要随意删除提示消息",
        None,
    ),
]
_MENU_TAIL: list[_MenuRow] = [_MENU_GAP, ("section", "未完待续", None)]

# 权限档在菜单描述尾部追加的说明，用户档不写
_ROLE_NOTE: dict[CommandRole, str] = {
    CommandRole.OWNER: "（仅主人）",
    CommandRole.ADMIN: "（需授权）",
}


def _flag_label(flag: HelpFlagDTO) -> str:
    """拼开关在帮助图与回执上的左列文本

    - 带值的开关在名后跟上值名，值名只作说明不参与解析
    """
    return f"{flag.name} {flag.value}" if flag.value else flag.name


def _build_menu_data() -> list[_MenuRow]:
    """聚合帮助菜单数据源

    - 插件段按启用序列拼接，与路由注册同序
    - 空 section 或 note 省略对应行
    - 命令行带上清单原条目
    - 每个有内容的插件块之前插一行空行
    """
    rows: list[_MenuRow] = [*_MENU_HEAD]
    for manifest in enabled_manifests(PROFILE_DIR / PluginFileName.STATE):
        block: list[_MenuRow] = []
        for section in manifest.help_section:
            if section.section:
                block.append(("section", section.section, None))
            if section.note:
                block.append(("note", section.note, None))
            for command in section.commands:
                block.append(("command", command.cmd, command))
        if block:
            rows.append(_MENU_GAP)
            rows.extend(block)
    rows.extend(_MENU_TAIL)
    return rows


_HELP = _HelpRenderConfig()


def _build_help_menu() -> tuple[
    dict[str, str], dict[str, HelpCommandDTO], list[_MenuEntry]
]:
    """构建帮助菜单数据

    - 登记的开关每个单占一条，紧跟所属命令条目
    - 权限档说明追加在描述尾部，用户档不带
    """
    help_list: dict[str, str] = {}
    command_specs: dict[str, HelpCommandDTO] = {}
    display_order: list[_MenuEntry] = []

    for item_type, content, command in _build_menu_data():
        if command is None:
            display_order.append((item_type, content, ""))
            continue
        desc = f"{command.desc}{_ROLE_NOTE.get(command.role, '')}"
        help_list[command.cmd] = desc
        command_specs[command.cmd] = command
        display_order.append(("command", command.cmd, desc))
        display_order.extend(
            ("flag", _flag_label(flag), flag.desc) for flag in command.flags
        )

    return help_list, command_specs, display_order


help_list, command_specs, _display_order = _build_help_menu()


def _menu_digest() -> str:
    """计算菜单内容指纹

    - 启用集与帮助文案全量参与，行序影响摘要
    - 排版参数一并参与，改行距也能触发重画
    """
    lines = [f"{item_type}|{label}|{note}" for item_type, label, note in _display_order]
    lines.insert(0, _layout_stamp())
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def _layout_stamp() -> str:
    """把排版参数拼成指纹的一段"""
    sizes = (
        _HELP.font_size,
        _HELP.line_spacing,
        _HELP.padding,
        _HELP.column_gap,
        _HELP.flag_indent,
    )
    return "layout|" + "|".join(str(size) for size in sizes)


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
    - 开关与参数各占描述下面的一行
    """
    desc = help_list.get(name)
    if desc is None:
        return BotMessage.CMD_FORMAT_ERROR
    spec = command_specs.get(name)
    if spec is None:
        return desc
    return f"{desc}\n{_usage_lines(spec)}"


def resolve_usage_hint(name: str) -> str:
    """取单命令的用法提示

    - 头一行点命令名，开关与参数两行同单命令帮助
    - 清单没这条命令时退回格式错误
    """
    spec = command_specs.get(name)
    if spec is None:
        return BotMessage.CMD_FORMAT_ERROR
    return f"{BotMessage.CMD_USAGE_HINT.format(cmd=name)}\n{_usage_lines(spec)}"


def _usage_lines(spec: HelpCommandDTO) -> str:
    """拼单命令的可用开关与可用参数

    - -h 全命令默认支持，清单 flag 追加其后
    - 开关说明只进帮助图，这两行只列名字与值名
    - 清单没登记 args 就不出参数行
    """
    switches = [CommandFlag.HELP, *(_flag_label(flag) for flag in spec.flags)]
    lines = [BotMessage.CMD_USAGE_FLAGS.format(flags="、".join(switches))]
    if spec.args:
        lines.append(BotMessage.CMD_USAGE_ARGS.format(args=spec.args))
    return "\n".join(lines)


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


def _render_menu(digest: str) -> Path:
    """绘制菜单图片并写指纹文件

    - 仅缓存未命中时调用
    - 左列取最宽一条定列宽，说明列按像素对齐
    - 段名与空行不分列，空行绘成整行留白
    """
    font = ImageFont.truetype(_FONT_PATH, _HELP.font_size)
    cells: list[tuple[str, str | None]] = []
    for item_type, label, note in _display_order:
        if item_type == "command":
            cells.append((f"/{label}", note))
        elif item_type == "flag":
            cells.append((f"{'':<{_HELP.flag_indent}}{label}", note))
        else:
            cells.append((label, None))

    padding = _HELP.padding
    left_width = max(
        (font.getlength(left) for left, note in cells if note is not None), default=0.0
    )
    desc_x = padding + left_width + _HELP.column_gap
    max_width = max(
        (
            desc_x + font.getlength(note) if note is not None else font.getlength(left)
            for left, note in cells
        ),
        default=0.0,
    )

    line_height = _HELP.line_spacing + _HELP.font_size
    img = Image.new(
        _HELP.color_mode,
        (int(max_width) + padding * 2, len(cells) * line_height + padding * 2),
        _HELP.bg_color,
    )
    dr = ImageDraw.Draw(img)

    for i, (left, note) in enumerate(cells):
        y = padding + i * line_height
        if note is None:
            dr.text((padding, y), left, font=font, fill=_HELP.text_color)
            continue
        dr.text((padding, y), left, font=font, fill=_HELP.text_color)
        dr.text((desc_x, y), note, font=font, fill=_HELP.text_color)

    # 图与指纹成对落盘，缺一即判缓存未命中
    _SAVE_PATH.parent.mkdir(parents=True, exist_ok=True)
    img.save(_SAVE_PATH)
    _DIGEST_PATH.write_text(digest, encoding="utf-8")
    return _SAVE_PATH
