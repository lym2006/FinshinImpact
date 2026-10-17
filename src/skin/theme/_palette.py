# src/skin/theme/_palette.py
"""跨层调色板

- 定义引导层与主界面共用的颜色与圆角
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class _PaletteTheme:
    """深色主题调色板

    - 字段按用途命名，消费方按用途取值
    """

    bg: str = "#1E1E1E"  # 窗口背景色
    color: str = "#D4D4D4"  # 文字色
    hover_bg: str = "#3A3A3A"  # 悬停背景色
    hover_color: str = "#FFFFFF"  # 悬停文字色
    pressed_bg: str = "#2A2A2A"  # 按下背景色
    sel_bg: str = "#264F78"  # 选中背景色
    sel_color: str = "#FFFFFF"  # 选中文字色
    input_bg: str = "#2D2D2D"  # 输入控件背景色
    item_bg: str = "#2D2D2D"  # 列表行背景色
    list_bg: str = "#3C3C3C"  # 列表容器底色，行缝隙露此色
    border_color: str = "#444444"  # 描边色
    disabled_color: str = "#808080"  # 置灰文字色
    danger_bg: str = "#D32F2F"  # 危险操作背景色
    danger_hover_bg: str = "#B71C1C"  # 危险操作悬停色
    danger_pressed_bg: str = "#9A0007"  # 危险操作按下色
    primary_hover_bg: str = "#2B5A8A"  # 主按钮悬停色
    primary_pressed_bg: str = "#1A4060"  # 主按钮按下色
    radius: int = 4  # 全局圆角


PALETTE = _PaletteTheme()
