"""主窗口样式

- 拼装主窗口与中央容器的全局 QSS
"""

from ..theme import (
    BODY,
    SCROLLBAR,
    TOOLBAR,
    ObjectName,
)
from ._base import Qss
from ._buttons import build_button_qss

# 主窗口与中央容器
_BODY_QSS = f"""\
QMainWindow, QWidget#{ObjectName.CENTRAL} {{
    background-color: {BODY.bg};
}}"""

# 工具栏
_TOOLBAR_QSS = f"""\
QWidget#{ObjectName.TOOLBAR} {{
    background-color: {TOOLBAR.bg};
    border-bottom: {TOOLBAR.border_width}px solid {TOOLBAR.border_color};
}}"""

# 仪表盘文本区域
_DASHBOARD_QSS = f"""\
QTextEdit#{ObjectName.DASHBOARD} {{
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

_GLOBAL_QSS = "\n".join(
    [
        _BODY_QSS,
        _TOOLBAR_QSS,
        build_button_qss(),
        _DASHBOARD_QSS,
        _SCROLLBAR_QSS,
    ]
)


def build_global_qss() -> Qss:
    """构建主窗口 QSS"""
    return Qss(_GLOBAL_QSS)
