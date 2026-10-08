# src/gui/_qss/_parts.py
"""弹窗样式片段

- 定义各弹窗共用的 QSS 片段常量
"""

from .._theme import (
    BODY,
    BTN,
    GLOBAL,
    LIST_DIALOG,
    SCROLLBAR,
    SETTINGS_DIALOG,
    TOOLBAR,
    WAIT_DIALOG,
)

# 弹窗专属 QSS

# 弹窗基本样式
DIALOG_BASE_QSS = f"""\
QDialog {{
    background-color: {BODY.bg};
}}"""

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

# 勾选框（bool 配置行通用）
_DIALOG_CHECK_QSS = f"""\
QCheckBox {{
    color: {BODY.color};
    spacing: {SETTINGS_DIALOG.check_spacing}px;
}}

QCheckBox::indicator {{
    width: {SETTINGS_DIALOG.check_size}px;
    height: {SETTINGS_DIALOG.check_size}px;
    border: {SETTINGS_DIALOG.border_width}px solid {SETTINGS_DIALOG.border_color};
    border-radius: {GLOBAL.radius}px;
    background-color: {TOOLBAR.bg};
}}

QCheckBox::indicator:checked {{
    background-color: {BODY.selection_bg};
    border-color: {BODY.selection_bg};
}}"""

# 忙碌等待弹窗
WAIT_QSS = f"""\
QLabel#wait_spinner {{
    font-size: {WAIT_DIALOG.spinner_font_size}px;
    color: {WAIT_DIALOG.spinner_color};
}}"""

# 标题
DIALOG_LABEL_QSS = f"""\
QLabel {{
    color: {BODY.color};
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

# 主按钮（高亮）
DIALOG_BUTTON_QSS = f"""\
QPushButton#btn_primary {{
    background-color: {BODY.selection_bg};
    color: {BODY.selection_color};
    border: none;
    border-radius: {GLOBAL.radius}px;
    padding: {BTN.padding_v}px {BTN.padding_h}px;
    min-width: {SETTINGS_DIALOG.btn_min_width}px;
}}

QPushButton#btn_primary:hover {{
    background-color: {SETTINGS_DIALOG.btn_hover_bg};
}}

QPushButton#btn_primary:pressed {{
    background-color: {SETTINGS_DIALOG.btn_pressed_bg};
}}

QPushButton#btn_reset {{
    background-color: transparent;
    color: {LIST_DIALOG.secondary_color};
    border: {LIST_DIALOG.item_border_width}px solid {LIST_DIALOG.secondary_border_color};
    border-radius: {GLOBAL.radius}px;
    padding: 0px;
    min-width: {SETTINGS_DIALOG.reset_btn_size}px;
    max-width: {SETTINGS_DIALOG.reset_btn_size}px;
    min-height: {SETTINGS_DIALOG.reset_btn_size}px;
    max-height: {SETTINGS_DIALOG.reset_btn_size}px;
    font-size: {SETTINGS_DIALOG.reset_btn_font}px;
}}

QPushButton#btn_reset:hover {{
    background-color: {BTN.hover_bg};
    color: {BODY.hover_color};
    border-color: {BTN.hover_bg};
}}

QPushButton#btn_reset:pressed {{
    background-color: {BTN.pressed_bg};
}}

QPushButton#btn_persona_open,
QPushButton#btn_persona_preview {{
    background-color: {LIST_DIALOG.primary_bg};
    color: {LIST_DIALOG.primary_color};
    border: none;
    border-radius: {GLOBAL.radius}px;
    padding: {LIST_DIALOG.btn_padding_v}px {LIST_DIALOG.btn_padding_h}px;
    min-width: {LIST_DIALOG.btn_min_width}px;
}}

QPushButton#btn_persona_open:hover,
QPushButton#btn_persona_preview:hover {{
    background-color: {SETTINGS_DIALOG.btn_hover_bg};
}}

QPushButton#btn_persona_open:pressed,
QPushButton#btn_persona_preview:pressed {{
    background-color: {SETTINGS_DIALOG.btn_pressed_bg};
}}

QTextEdit#persona_preview {{
    background-color: {SETTINGS_DIALOG.tab_bg};
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
        DIALOG_BUTTON_QSS,
        _DIALOG_SCROLL_QSS,
        _DIALOG_CHECK_QSS,
    ]
)

# 列表项 QSS 拼接
LIST_QSS = f"{_LIST_BTN_QSS}\n{_LIST_ITEM_QSS}"
