# src/plugins/AI/services/_render/_theme.py
"""渲染主题

- 定义 Design Tokens 与 CSS 生成
"""

from dataclasses import dataclass
from typing import Literal

from profile_env import ASSET_EMOJI_FONT_NAME, ASSET_FONT_NAME, ASSETS_DIR

# 产物落在实例数据目录，相对路径的层数绑死该深度，改绝对地址免疫目录搬迁
_FONT_URI = (ASSETS_DIR / ASSET_FONT_NAME).as_uri()
_EMOJI_FONT_URI = (ASSETS_DIR / ASSET_EMOJI_FONT_NAME).as_uri()

# 正文字体栈
_FONT_BODY = ("'SegUIEmoji'", "'MyMainFont'", "'Segoe UI Emoji'", "sans-serif")

# 代码等宽字体栈
_FONT_CODE = ("'Consolas'", "'Monaco'", "'Courier New'", "monospace")


@dataclass(frozen=True)
class RenderTheme:
    """渲染主题配置"""

    # 全局/Reset
    box_sizing: str = "border-box"  # 全局盒模型规则
    margin_reset: int = 0  # 首尾元素外边距重置
    margin_normal: tuple[float, float] = (0.25, 0.25)  # 块级元素默认外边距(上em, 下em)
    margin_small: tuple[float, float] = (0.05, 0.05)  # 列表项紧凑外边距(上em, 下em)
    code_block_padding_reset: int = 0  # 代码块内部重置内边距(px)

    # 字体
    font_body: tuple[str, ...] = _FONT_BODY
    font_code: tuple[str, ...] = _FONT_CODE
    font_paths: tuple[str, ...] = (_EMOJI_FONT_URI, _FONT_URI)  # 自定义字体文件路径

    # Body（正文）
    body_bg: str = "#ffffff"  # 背景色
    body_color: str = "#333333"  # 文字色
    body_font_size: int = 13  # 字体大小(px)
    body_line_height: float = 1.25  # 行高(比值)
    body_padding: int = 15  # 内边距(px)
    body_min_width: int = 580  # 最小宽度(px)
    body_max_width: int = 960  # 最大宽度(px)

    # Code（行内代码）
    code_bg: str = "#f0f0f0"  # 背景色
    code_color: str = "#e83e8c"  # 文字色
    code_padding: tuple[int, int] = (1, 4)  # 内边距(垂直px, 水平px)
    code_radius: int = 2  # 圆角(px)
    code_font_size: float = 0.85  # 字体大小(em)

    # Code Block（<pre> 代码块）
    code_block_border_width: int = 1  # 边框宽度(px)
    code_block_border_color: str = "#444444"  # 边框颜色
    code_block_padding: int = 6  # 内边距(px)
    code_block_radius: int = 3  # 圆角(px)
    code_block_margin: tuple[float, float] = (0.25, 0.0)  # 外边距(上em, 下em)
    code_block_font_size: int = 11  # 字体大小(px)
    code_block_line_height: float = 1.3  # 行高(比值)

    # Table（表格）
    table_border_color: str = "#dddddd"  # 边框颜色
    table_header_bg: str = "#f2f2f2"  # 表头背景色

    # Cell（表格单元格 th/td）
    cell_border_width: int = 1  # 边框宽度(px)
    cell_min_width: int = 80  # 最小宽度(px)
    cell_padding: tuple[int, int] = (2, 4)  # 内边距(垂直px, 水平px)

    # Blockquote（引用块）
    blockquote_bg: str = "#f8f9fa"  # 背景色
    blockquote_border_color: str = "#e338e6"  # 左边框颜色
    blockquote_border_width: int = 3  # 左边框宽度(px)
    blockquote_color: str = "#555555"  # 文字色
    blockquote_padding: tuple[int, int] = (5, 10)  # 内边距(垂直px, 水平px)
    blockquote_margin: tuple[float, float] = (0.5, 0.0)  # 外边距(上em, 下em)

    # 圆角(左上px, 右上px, 右下px, 左下px)
    blockquote_radius: tuple[int, int, int, int] = (0, 2, 2, 0)

    # HTML 元素
    html_bg: str = "#FFA500"  # 背景色
    html_padding: int = 10  # 内边距(px)

    # 派生 CSS 属性
    def font_css(self, name: Literal["body", "code"]) -> str:
        """生成字体 CSS"""
        return ", ".join(getattr(self, f"font_{name}"))

    @property
    def font_faces_css(self) -> str:
        """动态生成 @font-face"""
        # 字体栈成员自带引号，模板再包一层即无效声明，剥掉后统一由模板包
        tpl = "@font-face {{font-family: '{name}'; src: url('{path}') format('truetype'); }}"
        return f"\n{' ' * 8}".join(
            tpl.format(name=name.strip("'"), path=path)
            for name, path in zip(self.font_body, self.font_paths, strict=False)
        )

    # 派生间距属性
    @property
    def margin_normal_css(self) -> str:
        return " ".join(f"{v:g}em" for v in self.margin_normal)

    @property
    def margin_small_css(self) -> str:
        return " ".join(f"{v:g}em" for v in self.margin_small)

    @property
    def blockquote_margin_css(self) -> str:
        return " ".join(f"{v:g}em" for v in self.blockquote_margin)

    @property
    def code_block_margin_css(self) -> str:
        return " ".join(f"{v:g}em" for v in self.code_block_margin)

    @property
    def cell_padding_css(self) -> str:
        return " ".join(f"{v:d}px" for v in self.cell_padding)

    @property
    def code_padding_css(self) -> str:
        return " ".join(f"{v:d}px" for v in self.code_padding)

    @property
    def blockquote_padding_css(self) -> str:
        return " ".join(f"{v:d}px" for v in self.blockquote_padding)

    @property
    def blockquote_radius_css(self) -> str:
        return " ".join(f"{v:d}px" for v in self.blockquote_radius)


render_theme = RenderTheme()  # 实例化为全局单例
