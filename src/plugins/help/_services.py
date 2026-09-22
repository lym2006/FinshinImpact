# src/plugins/help/_services.py
"""帮助服务（内部实现）

- 定义帮助菜单数据源与自动构建
- 提供单命令解析与图片渲染
"""

import threading
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from utils import DOCS_DIR, ROOT_DIR, get_logger

# ==================== 内部配置与数据源 ====================

_SAVE_PATH = DOCS_DIR / "help.png"
_RENDER_LOCK = threading.Lock()
_FONT_PATH = ROOT_DIR / "assets/font.ttf"

_logger = get_logger("Plg.Help")


class HelpRenderConfig:
    """帮助菜单图片渲染配置"""

    font_size: int = 30
    line_spacing: int = 10  # 行间距
    padding: int = 15  # 画布边距
    cmd_desc_gap: int = 20  # 命令与描述间距
    bg_color: str = "#FFFFFF"  # 背景色
    text_color: str = "#000000"  # 文字颜色


# 帮助菜单的单一数据源
_HELP_MENU_DATA: list[dict[str, str]] = [
    {"type": "section", "content": "Fool 的功能列表"},
    {
        "type": "note",
        "content": "注：只有少量命令后可带参数，请不要删除机器人发出的提示消息",
    },
    {
        "type": "command",
        "cmd": "help",
        "desc": "查看帮助文档，命令后接 -h 可以单独查看该命令帮助",
    },
    {"type": "section", "content": "AI 部分"},
    {"type": "note", "content": "独立会话和思考过程"},
    {"type": "command", "cmd": "on", "desc": "开启 AI 对话"},
    {"type": "command", "cmd": "off", "desc": "关闭 AI 对话"},
    {
        "type": "command",
        "cmd": "md",
        "desc": "以markdown格式输出上一次回复内容（图片）",
    },
    {"type": "command", "cmd": "history", "desc": "显示历史记录（包括思考过程）"},
    {"type": "command", "cmd": "clear", "desc": "清空记忆"},
    {"type": "command", "cmd": "balance", "desc": "查看账户余额"},
    # {"type": "command", "cmd": "change", "desc": "更改 AI 人设"},
    # {"type": "command", "cmd": "system", "desc": "以 system 身份输入数据，用于添加人设、背景等"},
    {"type": "section", "content": "未完待续"},
]

_HELP = HelpRenderConfig()

# ==================== 自动构建器 ====================


def _build_help_menu() -> tuple[dict[str, str], list[tuple[str, str]]]:
    """构建帮助菜单数据"""
    help_list: dict[str, str] = {}
    display_order: list[tuple[str, str]] = []

    for item_ in _HELP_MENU_DATA:
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

# ==================== 业务处理函数 ====================


def resolve_single_help(text: str) -> str:
    """解析单命令请求"""
    try:
        cmd_part = text[: text.index("-")]
    except ValueError:
        return "格式错误"

    cmd = cmd_part.replace(" ", "").replace("/", "")
    return help_list.get(cmd, "格式错误")


def prewarm() -> None:
    """启动前强制重画帮助图

    每进程恰好一次；失败不阻断，首次请求补画。
    """
    try:
        with _RENDER_LOCK:
            _render_menu()
        _logger.debug("帮助菜单图片已刷新")
    except Exception as e:
        _logger.send_error("帮助菜单预热失败，首次请求时重试", e)


def generate_image() -> Path:
    """渲染或命中缓存帮助图

    锁双重检查保证只画一次。
    """
    if _SAVE_PATH.exists():
        return _SAVE_PATH
    with _RENDER_LOCK:
        if _SAVE_PATH.exists():
            return _SAVE_PATH
        return _render_menu()


def _render_menu() -> Path:
    """绘制菜单图片

    仅缓存未命中时调用。
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

    img = Image.new("RGB", (img_width, img_height), _HELP.bg_color)
    dr = ImageDraw.Draw(img)

    for i, line in enumerate(lines):
        dr.text(
            (padding, padding + i * line_height), line, font=font, fill=_HELP.text_color
        )

    # 保存并返回路径（常驻缓存，命中复用不删）
    _SAVE_PATH.parent.mkdir(parents=True, exist_ok=True)
    img.save(_SAVE_PATH)
    return _SAVE_PATH
