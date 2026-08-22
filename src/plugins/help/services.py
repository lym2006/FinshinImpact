# src/plugins/help/services.py
"""
帮助指令业务逻辑层

负责：
- 帮助菜单的数据源与自动构建
- 单命令帮助解析
- 帮助菜单图片渲染
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from utils import ROOT_DIR

# ==================== 1. 全局配置与数据源 ====================
_save_path = ROOT_DIR / "data/docs/out.png"
_font_path = ROOT_DIR / "assets/font.ttf"

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


# ==================== 2. 自动构建器 ====================
def _build_help_menu() -> tuple[dict[str, str], list[tuple[str, str]]]:
    """根据 _HELP_MENU_DATA 自动构建命令字典和渲染顺序列表"""
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


# ==================== 3. 业务处理函数 ====================
def resolve_single_help(text: str) -> str:
    """解析用户输入的单命令帮助请求

    Args:
        text: 包含命令的原始文本

    Returns:
        对应的帮助说明文本或错误提示
    """
    try:
        cmd_part = text[: text.index("-")]
    except ValueError:
        return "格式错误"

    cmd = cmd_part.replace(" ", "").replace("/", "")
    return help_list.get(cmd, "格式错误")


def generate_image() -> Path:
    """根据配置渲染帮助菜单图片"""
    font_size = 30
    line_height = font_size + 10
    padding = 15

    # 使用字体对象获取真实的像素宽度
    font = ImageFont.truetype(_font_path, font_size)

    # 1. 预计算所有行的文本和最大宽度
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
                gap = 20
                line = f"{prefix}{' ' * gap}{desc}"
                lines.append(line)
                max_width = max(max_width, font.getlength(line))

    # 2. 创建画布并绘制
    img_width = int(max_width) + padding * 2
    img_height = len(lines) * line_height + padding * 2

    img = Image.new("RGB", (img_width, img_height), (255, 255, 255))
    dr = ImageDraw.Draw(img)

    for i, line in enumerate(lines):
        dr.text((padding, padding + i * line_height), line, font=font, fill="#000000")

    # 3. 保存并返回路径
    Path(_save_path).unlink(missing_ok=True)
    img.save(_save_path)
    return _save_path
