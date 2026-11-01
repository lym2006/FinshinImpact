# src/skin/qss/_settings.py
"""配置面板 QSS 拼装

- 收纳配置弹窗的大类、标签页、输入、列表与滚动片段
- 按弹窗拼出配置编辑与列表两类成品串
"""

from ..theme import (
    BODY,
    BTN,
    GLOBAL,
    LIST_DIALOG,
    SCROLLBAR,
    SETTINGS_DIALOG,
    TOOLBAR,
    ButtonStyle,
    ObjectName,
)
from ._base import DIALOG_BASE_QSS, DIALOG_BUTTON_QSS, DIALOG_LABEL_QSS, Qss
from ._combo import build_combo_qss

# 标签页
_TAB_QSS = f"""\
QWidget#{ObjectName.TAB_CONTAINER} {{
    background-color: {SETTINGS_DIALOG.tab_bg};
}}

QTabWidget::pane {{
    border: {SETTINGS_DIALOG.border_width}px solid {SETTINGS_DIALOG.border_color};
    background-color: {BODY.bg};
}}

QTabBar::tab {{
    background-color: {SETTINGS_DIALOG.tab_bg};
    color: {BODY.color};
    padding: {SETTINGS_DIALOG.tab_padding_v}px {SETTINGS_DIALOG.tab_padding_h}px;
    min-width: {SETTINGS_DIALOG.tab_min_width}px;
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
    background-color: {BODY.selection_bg};
    color: {BODY.selection_color};
}}"""

# 左侧大类列表
_CATEGORY_QSS = f"""\
QListWidget#{ObjectName.CATEGORY_LIST} {{
    background-color: {SETTINGS_DIALOG.tab_bg};
    color: {BODY.color};
    border: {SETTINGS_DIALOG.border_width}px solid {SETTINGS_DIALOG.border_color};
    border-radius: {GLOBAL.radius}px;
    outline: none;
}}

QListWidget#{ObjectName.CATEGORY_LIST}::item {{
    padding: {SETTINGS_DIALOG.category_padding_v}px {SETTINGS_DIALOG.category_padding_h}px;
}}

QListWidget#{ObjectName.CATEGORY_LIST}::item:selected {{
    background-color: {BODY.selection_bg};
    color: {BODY.selection_color};
}}

QListWidget#{ObjectName.CATEGORY_LIST}::item:!selected:hover {{
    background-color: {BODY.hover_bg};
    color: {BODY.hover_color};
}}"""

# 单行输入
_LINEEDIT_QSS = f"""\
QLineEdit {{
    background-color: {TOOLBAR.bg};
    color: {BODY.color};
    border: {SETTINGS_DIALOG.border_width}px solid {SETTINGS_DIALOG.border_color};
    border-radius: {GLOBAL.radius}px;
    padding: {SETTINGS_DIALOG.input_padding_v}px {SETTINGS_DIALOG.input_padding_h}px;
}}

QLineEdit:focus {{
    border: {SETTINGS_DIALOG.border_width}px solid {BODY.selection_bg};
}}"""

# 文字编辑
_TEXTEDIT_QSS = f"""\
QTextEdit {{
    background-color: {TOOLBAR.bg};
    color: {BODY.color};
    border: {SETTINGS_DIALOG.border_width}px solid {SETTINGS_DIALOG.border_color};
    border-radius: {GLOBAL.radius}px;
    padding: {SETTINGS_DIALOG.input_padding_v}px {SETTINGS_DIALOG.input_padding_h}px;
    selection-background-color: {BODY.selection_bg};
    selection-color: {BODY.selection_color};
}}

QTextEdit:focus {{
    border: {SETTINGS_DIALOG.border_width}px solid {BODY.selection_bg};
}}"""

# 下拉选择
_COMBO_QSS = build_combo_qss(
    bg=TOOLBAR.bg,
    fg=BODY.color,
    border_color=SETTINGS_DIALOG.border_color,
    border_width=SETTINGS_DIALOG.border_width,
    radius=GLOBAL.radius,
    pad_v=SETTINGS_DIALOG.input_padding_v,
    pad_h=SETTINGS_DIALOG.input_padding_h,
    accent_border=BODY.selection_bg,
    sel_bg=BODY.selection_bg,
    sel_color=BODY.selection_color,
)

# 弹窗滚动条
_SCROLL_QSS = f"""
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
QPushButton#{ButtonStyle.LIST_ADD} {{
    background-color: {LIST_DIALOG.primary_bg};
    color: {LIST_DIALOG.primary_color};
    border: none;
    border-radius: {GLOBAL.radius}px;
    padding: {LIST_DIALOG.btn_padding_v}px {LIST_DIALOG.btn_padding_h}px;
    min-width: {LIST_DIALOG.btn_min_width}px;
}}

QPushButton#{ButtonStyle.LIST_ADD}:hover {{
    background-color: {LIST_DIALOG.primary_hover_bg};
}}

QPushButton#{ButtonStyle.LIST_DEL} {{
    background-color: transparent;
    color: {LIST_DIALOG.secondary_color};
    border: {LIST_DIALOG.item_border_width}px solid {LIST_DIALOG.secondary_border_color};
    border-radius: {GLOBAL.radius}px;
    padding: {LIST_DIALOG.btn_padding_v}px {LIST_DIALOG.btn_padding_h}px;
    min-width: {LIST_DIALOG.btn_min_width}px;
}}

QPushButton#{ButtonStyle.LIST_DEL}:hover {{
    border-color: {LIST_DIALOG.secondary_hover_border_color};
    color: {LIST_DIALOG.secondary_hover_color};
    background-color: {LIST_DIALOG.secondary_hover_bg};
}}
"""

# 列表项
_LIST_ITEM_QSS = f"""\
QListWidget#{ObjectName.LIST_WIDGET} {{
    background-color: {LIST_DIALOG.item_border_color};
    color: {BODY.color};
    border: {SETTINGS_DIALOG.border_width}px solid {SETTINGS_DIALOG.border_color};
    border-radius: {GLOBAL.radius}px;
    outline: none;
    margin: {LIST_DIALOG.container_inner_margin}px;
}}

QListWidget#{ObjectName.LIST_WIDGET}::item {{
    background-color: {TOOLBAR.bg}; 
    color: {BODY.color};
    margin-bottom: {LIST_DIALOG.item_border_width}px; 
    padding: {LIST_DIALOG.item_padding_v}px {LIST_DIALOG.item_padding_h}px;
}}

QListWidget#{ObjectName.LIST_WIDGET}::item:selected {{
    background-color: {BODY.selection_bg};
    color: {BODY.selection_color};
}}

QListWidget#{ObjectName.LIST_WIDGET}::item:hover {{
    background-color: {BODY.hover_bg};
}}"""

# 弹窗 QSS 拼接
_SETTINGS_DIALOG_QSS = "\n".join(
    [
        DIALOG_BASE_QSS,
        _TAB_QSS,
        _CATEGORY_QSS,
        DIALOG_LABEL_QSS,
        _LINEEDIT_QSS,
        _TEXTEDIT_QSS,
        _COMBO_QSS,
        DIALOG_BUTTON_QSS,
        _SCROLL_QSS,
    ]
)

# 列表项 QSS 拼接
_SETTINGS_LIST_QSS = f"{_LIST_BTN_QSS}\n{_LIST_ITEM_QSS}"


def build_settings_dialog_qss() -> Qss:
    """构建弹窗 QSS"""
    return Qss(_SETTINGS_DIALOG_QSS)


def build_settings_list_qss() -> Qss:
    """构建配置列表项 QSS"""
    return Qss(_SETTINGS_LIST_QSS)
