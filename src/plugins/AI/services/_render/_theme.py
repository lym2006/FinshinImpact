# src/plugins/AI/services/_render/_theme.py
"""渲染主题（内部实现）

- 定义 Design Tokens 与 CSS 生成
"""

from typing import Literal


class RenderTheme:
    """渲染主题配置"""

    def __init__(self) -> None:

        # ==================== 全局/Reset ====================

        self.box_sizing: str = "border-box"  # 全局盒模型规则
        self.margin_reset: int = 0  # 首尾元素外边距重置
        self.margin_normal: tuple[float, float] = (
            0.25,
            0.25,
        )  # 块级元素默认外边距(上em, 下em)
        self.margin_small: tuple[float, float] = (
            0.05,
            0.05,
        )  # 列表项紧凑外边距(上em, 下em)
        self.code_block_padding_reset: int = 0  # 代码块内部重置内边距(px)

        # ==================== 字体 ====================

        self.font_body: tuple[str, ...] = (
            "'SegUIEmoji'",
            "'MyMainFont'",
            "'Segoe UI Emoji'",
            "sans-serif",
        )  # 正文字体栈
        self.font_code: tuple[str, ...] = (
            "'Consolas'",
            "'Monaco'",
            "'Courier New'",
            "monospace",
        )  # 代码等宽字体栈
        self.font_paths: tuple[str, ...] = (
            "../../assets/seguiemj.ttf",
            "../../assets/font.ttf",
        )  # 自定义字体文件路径

        # ==================== Body（正文） ====================

        self.body_bg: str = "#ffffff"  # 背景色
        self.body_color: str = "#333333"  # 文字色
        self.body_font_size: int = 13  # 字体大小(px)
        self.body_line_height: float = 1.25  # 行高(比值)
        self.body_padding: int = 15  # 内边距(px)
        self.body_min_width: int = 580  # 最小宽度(px)
        self.body_max_width: int = 960  # 最大宽度(px)

        # ==================== Code（行内代码） ====================

        self.code_bg: str = "#f0f0f0"  # 背景色
        self.code_color: str = "#e83e8c"  # 文字色
        self.code_padding: tuple[int, int] = (1, 4)  # 内边距(垂直px, 水平px)
        self.code_radius: int = 2  # 圆角(px)
        self.code_font_size: float = 0.85  # 字体大小(em)

        # ==================== Code Block（<pre> 代码块） ====================

        self.code_block_border_width: int = 1  # 边框宽度(px)
        self.code_block_border_color: str = "#444444"  # 边框颜色
        self.code_block_padding: int = 6  # 内边距(px)
        self.code_block_radius: int = 3  # 圆角(px)
        self.code_block_margin: tuple[float, float] = (
            0.25,
            0.0,
        )  # 外边距(上em, 下em)
        self.code_block_font_size: int = 11  # 字体大小(px)
        self.code_block_line_height: float = 1.3  # 行高(比值)

        # ==================== Table（表格） ====================

        self.table_border_color: str = "#dddddd"  # 边框颜色
        self.table_header_bg: str = "#f2f2f2"  # 表头背景色

        # ==================== Cell（表格单元格 th/td） ====================

        self.cell_border_width: int = 1  # 边框宽度(px)
        self.cell_min_width: int = 80  # 最小宽度(px)
        self.cell_padding: tuple[int, int] = (2, 4)  # 内边距(垂直px, 水平px)

        # ==================== Blockquote（引用块） ====================

        self.blockquote_bg: str = "#f8f9fa"  # 背景色
        self.blockquote_border_color: str = "#e338e6"  # 左边框颜色
        self.blockquote_border_width: int = 3  # 左边框宽度(px)
        self.blockquote_color: str = "#555555"  # 文字色
        self.blockquote_padding: tuple[int, int] = (
            5,
            10,
        )  # 内边距(垂直px, 水平px)
        self.blockquote_margin: tuple[float, float] = (
            0.5,
            0.0,
        )  # 外边距(上em, 下em)
        self.blockquote_radius: tuple[int, int, int, int] = (
            0,
            2,
            2,
            0,
        )  # 圆角(左上px, 右上px, 右下px, 左下px)

        # ==================== HTML 元素 ====================

        self.html_bg: str = "#FFA500"  # 背景色
        self.html_padding: int = 10  # 内边距(px)

    # ==================== 动态计算 CSS 属性 ====================

    def font_css(self, name: Literal["body", "code"]) -> str:
        """生成字体 CSS"""
        return ", ".join(getattr(self, f"font_{name}"))

    @property
    def font_faces_css(self) -> str:
        """动态生成 @font-face"""
        tpl = "@font-face {{font-family: '{name}'; src: url('{path}') format('truetype'); }}"
        return f"\n{' ' * 8}".join(
            tpl.format(name=name, path=path)
            for name, path in zip(self.font_body, self.font_paths, strict=False)
        )

    # 批量生成 px 和 em 的元组拼接属性
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
