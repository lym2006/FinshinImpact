# src/gui/_qss/_parts.py
"""弹窗样式片段

- 定义各弹窗共用的 QSS 片段常量
"""

from skin.theme import (
    BODY,
    BTN,
    GLOBAL,
    LIST_DIALOG,
    SCROLLBAR,
    SETTINGS_DIALOG,
    TOOLBAR,
)
from widgets import (
    DIALOG_BASE_QSS,
    DIALOG_BUTTON_QSS,
    DIALOG_LABEL_QSS,
    ButtonStyle,
    build_combo_qss,
)

# 标签页
_DIALOG_TAB_QSS = f"""\
QWidget#{SETTINGS_DIALOG.tab_container_name} {{
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
    background-color: {BODY.bg};
    color: {BODY.hover_color};
}}"""

# 单行输入
_DIALOG_LINEEDIT_QSS = f"""\
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
_DIALOG_TEXTEDIT_QSS = f"""\
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
_DIALOG_COMBO_QSS = build_combo_qss(
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
QListWidget#list_widget {{
    background-color: {LIST_DIALOG.item_border_color};
    color: {BODY.color};
    border: {SETTINGS_DIALOG.border_width}px solid {SETTINGS_DIALOG.border_color};
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

DIALOG_QSS = "\n".join(  # 弹窗 QSS 拼接
    [
        DIALOG_BASE_QSS,
        _DIALOG_TAB_QSS,
        DIALOG_LABEL_QSS,
        _DIALOG_LINEEDIT_QSS,
        _DIALOG_TEXTEDIT_QSS,
        _DIALOG_COMBO_QSS,
        DIALOG_BUTTON_QSS,
        _DIALOG_SCROLL_QSS,
    ]
)

# 列表项 QSS 拼接
LIST_QSS = f"{_LIST_BTN_QSS}\n{_LIST_ITEM_QSS}"
