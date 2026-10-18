# src/skin/qss/_guide.py
"""引导窗 QSS 拼装

- 拼出引导各窗共用的 QSS
"""

from ..theme import (
    GUIDE_BTN,
    PANEL,
    ButtonStyle,
)
from ..theme import (
    PALETTE as SURFACE,
)
from ._base import Qss
from ._combo import build_combo_qss

# 引导期控件统一描边宽度（像素）
_BORDER_PX = 1

# 窗口与标签
_DARK_QSS = f"""\
QDialog {{
    background-color: {SURFACE.bg};
}}

QLabel {{
    color: {SURFACE.color};
    background-color: transparent;
}}"""

# 输入控件
_INPUT_QSS = f"""\
QLineEdit {{
    background-color: {SURFACE.input_bg};
    color: {SURFACE.color};
    border: 1px solid {SURFACE.border_color};
    border-radius: {SURFACE.radius}px;
    padding: {GUIDE_BTN.padding_v}px {GUIDE_BTN.padding_h // 2}px;
    selection-background-color: {SURFACE.sel_bg};
    selection-color: {SURFACE.sel_color};
}}

QLineEdit:focus {{
    border: 1px solid {SURFACE.sel_bg};
}}"""

# 下拉选择框
_COMBO_QSS = build_combo_qss(
    bg=SURFACE.input_bg,
    fg=SURFACE.color,
    border_color=SURFACE.border_color,
    border_width=_BORDER_PX,
    radius=SURFACE.radius,
    pad_v=GUIDE_BTN.padding_v,
    pad_h=GUIDE_BTN.padding_h // 2,
    accent_border=SURFACE.hover_bg,
    sel_bg=SURFACE.sel_bg,
    sel_color=SURFACE.sel_color,
)

# 按钮
_BUTTON_QSS = f"""\
QPushButton {{
    background-color: {SURFACE.input_bg};
    color: {SURFACE.color};
    border: none;
    border-radius: {SURFACE.radius}px;
    padding: {GUIDE_BTN.padding_v}px {GUIDE_BTN.padding_h}px;
    min-width: {GUIDE_BTN.min_width}px;
    min-height: {GUIDE_BTN.height}px;
}}

QPushButton:hover {{
    background-color: {SURFACE.hover_bg};
    color: {SURFACE.hover_color};
}}

QPushButton:pressed {{
    background-color: {SURFACE.pressed_bg};
}}

QPushButton:disabled {{
    color: {SURFACE.disabled_color};
    background-color: {SURFACE.bg};
}}

QPushButton#{ButtonStyle.PRIMARY} {{
    background-color: {SURFACE.sel_bg};
    color: {SURFACE.sel_color};
}}

QPushButton#{ButtonStyle.PRIMARY}:hover {{
    background-color: {SURFACE.primary_hover_bg};
}}

QPushButton#{ButtonStyle.PRIMARY}:pressed {{
    background-color: {SURFACE.primary_pressed_bg};
}}

QPushButton#{ButtonStyle.DANGER} {{
    background-color: {SURFACE.danger_bg};
    color: {SURFACE.sel_color};
}}

QPushButton#{ButtonStyle.DANGER}:hover {{
    background-color: {SURFACE.danger_hover_bg};
}}

QPushButton#{ButtonStyle.DANGER}:pressed {{
    background-color: {SURFACE.danger_pressed_bg};
}}

QPushButton#{ButtonStyle.DANGER}:disabled {{
    background-color: {SURFACE.bg};
    color: {SURFACE.disabled_color};
}}

QPushButton#{ButtonStyle.SECONDARY} {{
    background-color: transparent;
    color: {SURFACE.color};
    border: 1px solid {SURFACE.border_color};
}}

QPushButton#{ButtonStyle.SECONDARY}:hover {{
    background-color: {SURFACE.hover_bg};
    border: 1px solid {SURFACE.sel_bg};
    color: {SURFACE.hover_color};
}}

QPushButton#{ButtonStyle.SECONDARY}:disabled {{
    border: 1px solid {SURFACE.border_color};
}}

QPushButton#{ButtonStyle.START} {{
    background-color: {SURFACE.sel_bg};
    color: {SURFACE.sel_color};
    font-weight: bold;
    min-width: {GUIDE_BTN.start_width}px;
}}

QPushButton#{ButtonStyle.START}:hover {{
    background-color: {SURFACE.primary_hover_bg};
}}

QPushButton#{ButtonStyle.START}:pressed {{
    background-color: {SURFACE.primary_pressed_bg};
}}"""

# 下拉菜单
_MENU_QSS = f"""\
QMenu {{
    background-color: {SURFACE.input_bg};
    color: {SURFACE.color};
    border: 1px solid {SURFACE.border_color};
    padding: 4px;
}}

QMenu::item {{
    padding: {GUIDE_BTN.padding_v}px {GUIDE_BTN.padding_h}px;
    border-radius: {SURFACE.radius}px;
}}

QMenu::item:selected {{
    background-color: {SURFACE.hover_bg};
    color: {SURFACE.hover_color};
}}

QMenu::item:disabled {{
    color: {SURFACE.disabled_color};
}}

QMenu::item[danger="true"] {{
    color: {SURFACE.danger_bg};
}}

QMenu::item[danger="true"]:selected {{
    background-color: {SURFACE.danger_bg};
    color: {SURFACE.sel_color};
}}"""

# 列表
_LIST_QSS = f"""\
QListWidget {{
    background-color: {SURFACE.list_bg};
    color: {SURFACE.color};
    border: 1px solid {SURFACE.border_color};
    border-radius: {SURFACE.radius}px;
    outline: none;
}}

QListWidget::item {{
    background-color: {SURFACE.item_bg};
    color: {SURFACE.color};
    margin-bottom: 1px;
    padding: {PANEL.row_pad_v}px {PANEL.row_pad_h}px;
}}

QListWidget::item:selected {{
    background-color: {SURFACE.sel_bg};
    color: {SURFACE.sel_color};
}}

QListWidget::item:hover {{
    background-color: {SURFACE.hover_bg};
    color: {SURFACE.hover_color};
}}

QLabel#row_core_mark {{
    color: {SURFACE.disabled_color};
    background-color: transparent;
}}"""

# 滚动条
_SCROLL_QSS = f"""\
QScrollBar:vertical {{
    background: {SURFACE.bg};
    width: 10px;
    border: none;
}}

QScrollBar::handle:vertical {{
    background: {SURFACE.hover_bg};
    border-radius: 5px;
    min-height: 20px;
}}

QScrollBar::handle:vertical:hover {{
    background: {SURFACE.border_color};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}"""

# 进度日志区
_PROGRESS_QSS = f"""\
QPlainTextEdit#progress_log {{
    background-color: {SURFACE.list_bg};
    color: {SURFACE.color};
    border: 1px solid {SURFACE.border_color};
    border-radius: {SURFACE.radius}px;
}}"""

# 启动等待窗
_LAUNCH_QSS = f"""\
QLabel#launch_text {{
    color: {SURFACE.color};
    font-weight: bold;
    background-color: transparent;
}}

QLabel#launch_note {{
    color: {SURFACE.disabled_color};
    background-color: transparent;
}}"""

_BOOTSTRAP_QSS = "\n".join(  # 引导期各窗共用皮肤
    [
        _DARK_QSS,
        _INPUT_QSS,
        _COMBO_QSS,
        _BUTTON_QSS,
        _MENU_QSS,
        _LIST_QSS,
        _SCROLL_QSS,
        _PROGRESS_QSS,
        _LAUNCH_QSS,
    ]
)


def build_bootstrap_qss() -> Qss:
    """构建引导期窗口 QSS"""
    return Qss(_BOOTSTRAP_QSS)
