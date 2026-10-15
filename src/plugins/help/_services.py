# src/plugins/help/_services.py
"""帮助服务

- 按插件清单与实例启用集聚合菜单数据源
- 提供单命令解析与图片渲染
"""

import hashlib
import threading
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from core.domain import PluginFile
from profile_env import ASSET_FONT_NAME, ASSETS_DIR
from utils import get_logger
from utils.paths import HELP_IMAGE, PROFILE_DIR
from utils.plugin import enabled_manifests

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
    color_mode: str = "RGB"  # PIL 色彩模式
    bg_color: str = "#FFFFFF"  # 背景色
    text_color: str = "#000000"  # 文字颜色


# 帮助图首尾两段全局说明，不挂任何插件
_MENU_HEAD: list[dict[str, str]] = [
    {"type": "section", "content": "Fool 的功能列表"},
    {
        "type": "note",
        "content": "注：只有少量命令后可带参数，请不要删除机器人发出的提示消息",
    },
]
_MENU_TAIL: list[dict[str, str]] = [{"type": "section", "content": "未完待续"}]


def _build_menu_data() -> list[dict[str, str]]:
    """聚合帮助菜单数据源

    - 插件段按启用序列拼接，与路由注册同序
    - 空 section 或 note 省略对应行
    """
    rows: list[dict[str, str]] = [*_MENU_HEAD]
    for manifest in enabled_manifests(PROFILE_DIR / PluginFile.STATE):
        for section in manifest.help_section:
            if section.section:
                rows.append({"type": "section", "content": section.section})
            if section.note:
                rows.append({"type": "note", "content": section.note})
            for command in section.commands:
                rows.append(
                    {"type": "command", "cmd": command.cmd, "desc": command.desc}
                )
    rows.extend(_MENU_TAIL)
    return rows


_HELP = _HelpRenderConfig()


def _build_help_menu() -> tuple[dict[str, str], list[tuple[str, str]]]:
    """构建帮助菜单数据"""
    help_list: dict[str, str] = {}
    display_order: list[tuple[str, str]] = []

    for item_ in _build_menu_data():
        match item_["type"]:
            case "command":
                cmd = item_["cmd"]
                desc = item_["desc"]
                help_list[cmd] = desc
                display_order.append(("command", cmd))
            case "section" | "note" as item_type:
                display_order.append((item_type, item_["content"]))

    return help_list, display_order


help_list, _display_order = _build_help_menu()


def _menu_digest() -> str:
    """计算菜单内容指纹

    - 启用集与帮助文案全量参与，行序影响摘要
    """
    lines = [
        f"{item_type}|{content}|{help_list.get(content, '')}"
        for item_type, content in _display_order
    ]
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


def resolve_single_help(text: str) -> str:
    """解析单命令请求"""
    try:
        cmd_part = text[: text.index("-")]
    except ValueError:
        return "格式错误"

    cmd = cmd_part.replace(" ", "").replace("/", "")
    return help_list.get(cmd, "格式错误")


def prewarm() -> None:
    """启动前按菜单指纹决定是否重画帮助图

    - 指纹相同即复用现图，不重画
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
    """
    # 使用字体对象获取真实的像素宽度
    font = ImageFont.truetype(_FONT_PATH, _HELP.font_size)

    # 预计算所有行的文本和最大宽度
    lines: list[str] = []
    max_width: float = 0.0

    for item_type, content in _display_order:
        match item_type:
            case "section" | "note":
                lines.append(content)
                max_width = max(max_width, font.getlength(content))
            case "command":
                desc = help_list[content]
                prefix = f"/{content}"
                line = f"{prefix:<{_HELP.cmd_desc_gap}}{desc}"
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

    # 保存并返回路径（图与指纹成对落盘，指纹命中即复用）
    _SAVE_PATH.parent.mkdir(parents=True, exist_ok=True)
    img.save(_SAVE_PATH)
    _DIGEST_PATH.write_text(digest, encoding="utf-8")
    return _SAVE_PATH
