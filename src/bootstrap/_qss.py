# src/bootstrap/_qss.py
"""引导期样式装配

- 拼出选窗、表单窗、插件面板、进度窗共用的 QSS
"""

from ._theme import (
    BTN,
    PANEL,
    SURFACE,
)

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
    padding: {BTN.padding_v}px {BTN.padding_h // 2}px;
    selection-background-color: {SURFACE.sel_bg};
    selection-color: {SURFACE.sel_color};
}}

QLineEdit:focus {{
    border: 1px solid {SURFACE.sel_bg};
}}

QComboBox {{
    background-color: {SURFACE.input_bg};
    color: {SURFACE.color};
    border: 1px solid {SURFACE.border_color};
    border-radius: {SURFACE.radius}px;
    padding: {BTN.padding_v}px {BTN.padding_h // 2}px;
}}

QComboBox:hover {{
    border: 1px solid {SURFACE.hover_bg};
}}

QComboBox QAbstractItemView {{
    background-color: {SURFACE.input_bg};
    color: {SURFACE.color};
    border: 1px solid {SURFACE.border_color};
    selection-background-color: {SURFACE.sel_bg};
    selection-color: {SURFACE.sel_color};
}}"""

# 按钮
_BUTTON_QSS = f"""\
QPushButton {{
    background-color: {SURFACE.input_bg};
    color: {SURFACE.color};
    border: none;
    border-radius: {SURFACE.radius}px;
    padding: {BTN.padding_v}px {BTN.padding_h}px;
    min-width: {BTN.min_width}px;
    min-height: {BTN.height}px;
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

QPushButton#btn_primary {{
    background-color: {SURFACE.sel_bg};
    color: {SURFACE.sel_color};
}}

QPushButton#btn_primary:hover {{
    background-color: {SURFACE.primary_hover_bg};
}}

QPushButton#btn_primary:pressed {{
    background-color: {SURFACE.primary_pressed_bg};
}}

QPushButton#btn_danger {{
    background-color: {SURFACE.danger_bg};
    color: {SURFACE.sel_color};
}}

QPushButton#btn_danger:hover {{
    background-color: {SURFACE.danger_hover_bg};
}}

QPushButton#btn_danger:pressed {{
    background-color: {SURFACE.danger_pressed_bg};
}}

QFrame#btn_sep {{
    color: {SURFACE.border_color};
    max-width: 1px;
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

_BOOTSTRAP_QSS = "\n".join(  # 引导期三窗共用皮肤
    [
        _DARK_QSS,
        _INPUT_QSS,
        _BUTTON_QSS,
        _LIST_QSS,
        _SCROLL_QSS,
        _PROGRESS_QSS,
    ]
)


def build_bootstrap_qss() -> str:
    """构建引导期窗口 QSS"""
    return _BOOTSTRAP_QSS
