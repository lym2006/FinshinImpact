# src/gui/_qss/_global.py
"""主窗口样式

- 拼装主窗口与中央容器的全局 QSS
"""

from .._theme import (
    BODY,
    BTN,
    BTN_DANGER,
    GLOBAL,
    SCROLLBAR,
    TOOLBAR,
)

# QSS 样式表

# 主窗口与中央容器
_BODY_QSS = f"""\
QMainWindow, QWidget#centralWidget {{
    background-color: {BODY.bg};
}}"""

# 工具栏
_TOOLBAR_QSS = f"""\
QWidget#toolbar {{
    background-color: {TOOLBAR.bg};
    border-bottom: {TOOLBAR.border_width}px solid {TOOLBAR.border_color};
}}"""

# 按钮
_BUTTON_QSS = f"""\
QPushButton {{
    background-color: {BTN.bg};
    color: {BODY.color};
    border: none;
    border-radius: {GLOBAL.radius}px;
    padding: {BTN.padding_v}px {BTN.padding_h}px;
    font-weight: bold;
    min-width: {BTN.min_width}px;
    min-height: {BTN.height}px;
}}

QPushButton:hover {{
    background-color: {BTN.hover_bg};
    color: {BODY.hover_color};
}}

QPushButton:pressed {{
    background-color: {BTN.pressed_bg};
}}"""

# 危险按钮
_BUTTON_DANGER_QSS = f"""\
QPushButton#btn_clear, QPushButton#btn_shutdown {{
    background-color: {BTN_DANGER.bg};
}}

QPushButton#btn_clear:hover, QPushButton#btn_shutdown:hover {{
    background-color: {BTN_DANGER.hover_bg};
}}

QPushButton#btn_clear:pressed, QPushButton#btn_shutdown:pressed {{
    background-color: {BTN_DANGER.pressed_bg};
}}"""

# 仪表盘文本区域
_DASHBOARD_QSS = f"""\
QTextEdit#dashboard {{
    background-color: {BODY.bg};
    color: {BODY.color};
    border: none;
    padding: {BODY.padding}px;
    selection-background-color: {BODY.selection_bg};
    selection-color: {BODY.hover_color};
}}"""

# 滚动条
_SCROLLBAR_QSS = f"""
QScrollBar:vertical {{
    background: {SCROLLBAR.bg};
    width: {SCROLLBAR.width}px;
    border: none;
    margin: {SCROLLBAR.margin}px;
}}

QScrollBar::handle:vertical {{
    background: {SCROLLBAR.handle_bg};
    border-radius: {SCROLLBAR.width // 2}px;
    min-height: {SCROLLBAR.min_handle_height}px;
}}

QScrollBar::handle:vertical:hover {{
    background: {SCROLLBAR.handle_hover_bg};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: {SCROLLBAR.arrow_height}px;
}}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}"""

_GLOBAL_QSS = "\n".join(  # 全局 QSS 拼接
    [
        _BODY_QSS,
        _TOOLBAR_QSS,
        _BUTTON_QSS,
        _BUTTON_DANGER_QSS,
        _DASHBOARD_QSS,
        _SCROLLBAR_QSS,
    ]
)


def build_global_qss() -> str:
    """构建主窗口 QSS"""
    return _GLOBAL_QSS
