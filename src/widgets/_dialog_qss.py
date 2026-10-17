# src/widgets/_dialog_qss.py
"""通用弹窗样式

- 收纳通知窗与等待窗共用的 QSS 片段
- 片段同时供配置类弹窗装配
"""

from skin.theme import (
    BODY,
    BTN,
    GLOBAL,
    LIST_DIALOG,
    SETTINGS_DIALOG,
    WAIT_DIALOG,
)

from ._factory import ButtonStyle

# 弹窗基本样式
DIALOG_BASE_QSS = f"""\
QDialog {{
    background-color: {BODY.bg};
}}"""

# 标题
DIALOG_LABEL_QSS = f"""\
QLabel {{
    color: {BODY.color};
}}"""

# 主按钮（高亮）
DIALOG_BUTTON_QSS = f"""\
QPushButton#{ButtonStyle.PRIMARY} {{
    background-color: {BODY.selection_bg};
    color: {BODY.selection_color};
    border: none;
    border-radius: {GLOBAL.radius}px;
    padding: {BTN.padding_v}px {BTN.padding_h}px;
    min-width: {SETTINGS_DIALOG.btn_min_width}px;
}}

QPushButton#{ButtonStyle.PRIMARY}:hover {{
    background-color: {SETTINGS_DIALOG.btn_hover_bg};
}}

QPushButton#{ButtonStyle.PRIMARY}:pressed {{
    background-color: {SETTINGS_DIALOG.btn_pressed_bg};
}}

QPushButton#{ButtonStyle.RESET} {{
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

QPushButton#{ButtonStyle.RESET}:hover {{
    background-color: {BTN.hover_bg};
    color: {BODY.hover_color};
    border-color: {BTN.hover_bg};
}}

QPushButton#{ButtonStyle.RESET}:pressed {{
    background-color: {BTN.pressed_bg};
}}

QPushButton#{ButtonStyle.PERSONA_OPEN},
QPushButton#{ButtonStyle.PERSONA_PREVIEW} {{
    background-color: {LIST_DIALOG.primary_bg};
    color: {LIST_DIALOG.primary_color};
    border: none;
    border-radius: {GLOBAL.radius}px;
    padding: {LIST_DIALOG.btn_padding_v}px {LIST_DIALOG.btn_padding_h}px;
    min-width: {LIST_DIALOG.btn_min_width}px;
}}

QPushButton#{ButtonStyle.PERSONA_OPEN}:hover,
QPushButton#{ButtonStyle.PERSONA_PREVIEW}:hover {{
    background-color: {SETTINGS_DIALOG.btn_hover_bg};
}}

QPushButton#{ButtonStyle.PERSONA_OPEN}:pressed,
QPushButton#{ButtonStyle.PERSONA_PREVIEW}:pressed {{
    background-color: {SETTINGS_DIALOG.btn_pressed_bg};
}}

QTextEdit#persona_preview {{
    background-color: {SETTINGS_DIALOG.tab_bg};
}}"""

# 忙碌等待弹窗
WAIT_QSS = f"""\
QLabel#wait_spinner {{
    font-size: {WAIT_DIALOG.spinner_font_size}px;
    color: {WAIT_DIALOG.spinner_color};
}}"""


def build_notice_dialog_qss() -> str:
    """构建通知弹窗 QSS"""
    return "\n".join(
        [
            DIALOG_BASE_QSS,
            DIALOG_LABEL_QSS,
            DIALOG_BUTTON_QSS,
        ]
    )


def build_wait_dialog_qss() -> str:
    """构建忙碌等待弹窗 QSS"""
    return "\n".join(
        [
            DIALOG_BASE_QSS,
            DIALOG_LABEL_QSS,
            DIALOG_BUTTON_QSS,
            WAIT_QSS,
        ]
    )


def build_combo_qss(
    *,
    bg: str,
    fg: str,
    border_color: str,
    border_width: int,
    radius: int,
    pad_v: int,
    pad_h: int,
    accent_border: str,
    sel_bg: str,
    sel_color: str,
) -> str:
    """拼下拉选择框 QSS

    - 弹层与框体共用底色和文字色
    - 悬停与聚焦共用一条强调描边
    """
    return f"""\
QComboBox {{
    background-color: {bg};
    color: {fg};
    border: {border_width}px solid {border_color};
    border-radius: {radius}px;
    padding: {pad_v}px {pad_h}px;
}}

QComboBox:hover,
QComboBox:focus {{
    border: {border_width}px solid {accent_border};
}}

QComboBox QAbstractItemView {{
    background-color: {bg};
    color: {fg};
    selection-background-color: {sel_bg};
    selection-color: {sel_color};
    border: {border_width}px solid {border_color};
    outline: none;
}}"""
