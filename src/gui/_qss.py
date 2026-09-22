# src/gui/_qss.py
"""QSS 拼装（内部实现）

- 实现组件样式渲染与 QSS 拼接
"""

from ._theme import (
    BODY,
    BTN,
    BTN_DANGER,
    GLOBAL,
    LIST_DIALOG,
    PROXY_DIALOG,  # noqa: F401 诊断弹窗构建器使用
    SCROLLBAR,
    TOOLBAR,
)
from ._theme import (
    CHANGE_DIALOG as CHANGE,
)
from ._theme import SETTINGS_DIALOG as DIALOG
from ._theme import WAIT_DIALOG as WAIT

# ==================== QSS 样式表 ====================

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

# 全局 QSS 拼接
_GLOBAL_QSS = "\n".join(
    [
        _BODY_QSS,
        _TOOLBAR_QSS,
        _BUTTON_QSS,
        _BUTTON_DANGER_QSS,
        _DASHBOARD_QSS,
        _SCROLLBAR_QSS,
    ]
)

# ==================== 弹窗专属 QSS ====================

# 弹窗基本样式
_DIALOG_BASE_QSS = f"""\
QDialog {{
    background-color: {BODY.bg};
}}"""

# 标签页
_DIALOG_TAB_QSS = f"""\
QTabWidget::pane {{
    border: {DIALOG.border_width}px solid {DIALOG.border_color};
    background-color: {BODY.bg};
}}

QTabBar::tab {{
    background-color: {DIALOG.tab_bg};
    color: {BODY.color};
    padding: {DIALOG.tab_padding_v}px {DIALOG.tab_padding_h}px;
    min-width: {DIALOG.tab_min_width}px;
    border-top-left-radius: {GLOBAL.radius}px;
    border-top-right-radius: {GLOBAL.radius}px;
}}

QTabBar::tab:!selected:hover {{
    background-color: {BODY.hover_bg};
    color: {BODY.hover_color};
}}

QTabBar::tab:!selected:pressed {{
    background-color: {BTN.pressed_bg};
}}

QTabBar::tab:selected {{
    background-color: {BODY.bg};
    color: {BODY.hover_color};
}}"""

# 勾选框（bool 配置行通用）
_DIALOG_CHECK_QSS = f"""\
QCheckBox {{
    color: {BODY.color};
    spacing: {DIALOG.check_spacing}px;
}}

QCheckBox::indicator {{
    width: {DIALOG.check_size}px;
    height: {DIALOG.check_size}px;
    border: {DIALOG.border_width}px solid {DIALOG.border_color};
    border-radius: {GLOBAL.radius}px;
    background-color: {TOOLBAR.bg};
}}

QCheckBox::indicator:checked {{
    background-color: {BODY.selection_bg};
    border-color: {BODY.selection_bg};
}}"""

# 忙碌等待弹窗
_WAIT_QSS = f"""\
QLabel#wait_spinner {{
    font-size: {WAIT.spinner_font_size}px;
    color: {WAIT.spinner_color};
}}"""

# 标题
_DIALOG_LABEL_QSS = f"""\
QLabel {{
    color: {BODY.color};
}}"""

# 单行输入
_DIALOG_LINEEDIT_QSS = f"""\
QLineEdit {{
    background-color: {TOOLBAR.bg};
    color: {BODY.color};
    border: {DIALOG.border_width}px solid {DIALOG.border_color};
    border-radius: {GLOBAL.radius}px;
    padding: {DIALOG.input_padding_v}px {DIALOG.input_padding_h}px;
}}

QLineEdit:focus {{
    border: {DIALOG.border_width}px solid {BODY.selection_bg};
}}"""

# 文字编辑
_DIALOG_TEXTEDIT_QSS = f"""\
QTextEdit {{
    background-color: {TOOLBAR.bg};
    color: {BODY.color};
    border: {DIALOG.border_width}px solid {DIALOG.border_color};
    border-radius: {GLOBAL.radius}px;
    padding: {DIALOG.input_padding_v}px {DIALOG.input_padding_h}px;
    selection-background-color: {BODY.selection_bg};
    selection-color: {BODY.selection_color};
}}

QTextEdit:focus {{
    border: {DIALOG.border_width}px solid {BODY.selection_bg};
}}"""

# 主按钮（高亮）
_DIALOG_BUTTON_QSS = f"""\
QPushButton#btn_primary {{
    background-color: {BODY.selection_bg};
    color: {BODY.selection_color};
    border: none;
    border-radius: {GLOBAL.radius}px;
    padding: {BTN.padding_v}px {BTN.padding_h}px;
    min-width: {DIALOG.btn_min_width}px;
}}

QPushButton#btn_primary:hover {{
    background-color: {DIALOG.btn_hover_bg};
}}

QPushButton#btn_primary:pressed {{
    background-color: {DIALOG.btn_pressed_bg};
}}"""

# 弹窗滚动条
_DIALOG_SCROLL_QSS = f"""
QScrollArea > QWidget > QWidget {{
    background-color: {BODY.bg};
}}

QScrollArea > QScrollBar:vertical {{
    background-color: {TOOLBAR.bg};
    width: {SCROLLBAR.width}px;
    border: none;
    margin: {SCROLLBAR.margin}px;
}}

QScrollArea > QScrollBar::handle:vertical {{
    background-color: {SCROLLBAR.handle_bg};
    border-radius: {SCROLLBAR.width // 2}px;
    min-height: {SCROLLBAR.min_handle_height}px;
}}

QScrollArea > QScrollBar::handle:vertical:hover {{
    background-color: {SCROLLBAR.handle_hover_bg};
}}

QScrollArea > QScrollBar::add-line:vertical,
QScrollArea > QScrollBar::sub-line:vertical {{
    height: {SCROLLBAR.arrow_height}px;
}}"""

# 列表字段底部工具栏按钮
_LIST_BTN_QSS = f"""\
QPushButton#btn_list_add {{
    background-color: {LIST_DIALOG.primary_bg};
    color: {LIST_DIALOG.primary_color};
    border: none;
    border-radius: {GLOBAL.radius}px;
    padding: {LIST_DIALOG.btn_padding_v}px {LIST_DIALOG.btn_padding_h}px;
    min-width: {LIST_DIALOG.btn_min_width}px;
}}

QPushButton#btn_list_add:hover {{
    background-color: {LIST_DIALOG.primary_hover_bg};
}}

QPushButton#btn_list_del {{
    background-color: transparent;
    color: {LIST_DIALOG.secondary_color};
    border: {LIST_DIALOG.item_border_width}px solid {LIST_DIALOG.secondary_border_color};
    border-radius: {GLOBAL.radius}px;
    padding: {LIST_DIALOG.btn_padding_v}px {LIST_DIALOG.btn_padding_h}px;
    min-width: {LIST_DIALOG.btn_min_width}px;
}}

QPushButton#btn_list_del:hover {{
    border-color: {LIST_DIALOG.secondary_hover_border_color};
    color: {LIST_DIALOG.secondary_hover_color};
    background-color: {LIST_DIALOG.secondary_hover_bg};
}}
"""

# 列表项
_LIST_ITEM_QSS = f"""\
QListWidget#list_widget {{
    background-color: {LIST_DIALOG.item_border_color};
    color: {BODY.color};
    border: {DIALOG.border_width}px solid {DIALOG.border_color};
    border-radius: {GLOBAL.radius}px;
    outline: none;
    margin: {LIST_DIALOG.container_inner_margin}px;
}}

QListWidget#list_widget::item {{
    background-color: {TOOLBAR.bg}; 
    color: {BODY.color};
    margin-bottom: {LIST_DIALOG.item_border_width}px; 
    padding: {LIST_DIALOG.item_padding_v}px {LIST_DIALOG.item_padding_h}px;
}}

QListWidget#list_widget::item:selected {{
    background-color: {BODY.selection_bg};
    color: {BODY.selection_color};
}}

QListWidget#list_widget::item:hover {{
    background-color: {BODY.hover_bg};
}}"""

# 弹窗 QSS 拼接
_DIALOG_QSS = "\n".join(
    [
        _DIALOG_BASE_QSS,
        _DIALOG_TAB_QSS,
        _DIALOG_LABEL_QSS,
        _DIALOG_LINEEDIT_QSS,
        _DIALOG_TEXTEDIT_QSS,
        _DIALOG_BUTTON_QSS,
        _DIALOG_SCROLL_QSS,
        _DIALOG_CHECK_QSS,
    ]
)

# 变更确认表格
_CHANGE_TABLE_QSS = f"""\
QTableWidget#change_table {{
    background-color: {BODY.bg};
    alternate-background-color: {CHANGE.alt_bg};
    color: {BODY.color};
    border: {DIALOG.border_width}px solid {DIALOG.border_color};
    border-radius: {GLOBAL.radius}px;
    gridline-color: {CHANGE.grid_color};
}}

QTableWidget#change_table::item {{
    padding: {LIST_DIALOG.item_padding_v}px {LIST_DIALOG.item_padding_h}px;
}}

QTextEdit#change_cell {{
    background-color: {CHANGE.alt_bg};
    color: {BODY.color};
    border: none;
    padding: {CHANGE.cell_padding_v}px {CHANGE.cell_padding_h}px;
}}

QHeaderView::section {{
    background-color: {DIALOG.tab_bg};
    color: {BODY.hover_color};
    border: none;
    padding: {LIST_DIALOG.item_padding_v}px {LIST_DIALOG.item_padding_h}px;
}}"""

# 网络诊断弹窗
_PROXY_QSS = f"""\
QDialog {{
    background-color: {BODY.bg};
}}

QTextEdit#proxy_view {{
    background-color: {TOOLBAR.bg};
    color: {BODY.color};
    border: {DIALOG.border_width}px solid {DIALOG.border_color};
    border-radius: {GLOBAL.radius}px;
    padding: {DIALOG.input_padding_v}px {DIALOG.input_padding_h}px;
}}"""

# 列表项 QSS 拼接
_LIST_QSS = f"{_LIST_BTN_QSS}\n{_LIST_ITEM_QSS}"

# ==================== QSS 生成器 ====================


def build_global_qss() -> str:
    """构建主窗口 QSS"""
    return _GLOBAL_QSS


def build_settings_dialog_qss() -> str:
    """构建弹窗 QSS"""
    return _DIALOG_QSS


def build_settings_list_qss() -> str:
    """构建配置列表项 QSS"""
    return _LIST_QSS


def build_proxy_dialog_qss() -> str:
    """构建网络诊断弹窗 QSS"""
    return "\n".join(
        [
            _DIALOG_BASE_QSS,
            _DIALOG_BUTTON_QSS,
            _PROXY_QSS,
        ]
    )


def build_hint_dialog_qss() -> str:
    """构建通用提示弹窗 QSS"""
    return "\n".join(
        [
            _DIALOG_BASE_QSS,
            _DIALOG_LABEL_QSS,
            _DIALOG_BUTTON_QSS,
        ]
    )


def build_change_dialog_qss() -> str:
    """构建变更确认弹窗 QSS"""
    return "\n".join(
        [
            _DIALOG_BASE_QSS,
            _DIALOG_LABEL_QSS,
            _DIALOG_BUTTON_QSS,
            _CHANGE_TABLE_QSS,
        ]
    )


def build_wait_dialog_qss() -> str:
    """构建忙碌等待弹窗 QSS"""
    return "\n".join(
        [
            _DIALOG_BASE_QSS,
            _DIALOG_LABEL_QSS,
            _DIALOG_BUTTON_QSS,
            _WAIT_QSS,
        ]
    )
