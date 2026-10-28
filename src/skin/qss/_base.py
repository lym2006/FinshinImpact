# src/skin/qss/_base.py
"""QSS 基础件

- 定义 Qss 串类型与各弹窗共用的通用片段
- 装配公共弹窗三件并追加各面专属尾巴
"""

from typing import NewType

from ..theme import (
    BODY,
    BTN,
    BTN_DANGER,
    GLOBAL,
    LIST_DIALOG,
    SETTINGS_DIALOG,
    WAIT_DIALOG,
    ButtonStyle,
    ObjectName,
)

# 装配完成的 QSS 串，各 build_*_qss 的出口类型
Qss = NewType("Qss", str)

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

# 主按钮（高亮）与危险按钮
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

QPushButton#{ButtonStyle.DANGER} {{
    background-color: {BTN_DANGER.bg};
    color: {BODY.selection_color};
    border: none;
    border-radius: {GLOBAL.radius}px;
    padding: {BTN.padding_v}px {BTN.padding_h}px;
    min-width: {SETTINGS_DIALOG.btn_min_width}px;
}}

QPushButton#{ButtonStyle.DANGER}:hover {{
    background-color: {BTN_DANGER.hover_bg};
}}

QPushButton#{ButtonStyle.DANGER}:pressed {{
    background-color: {BTN_DANGER.pressed_bg};
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

QPushButton#{ButtonStyle.PERSONA} {{
    background-color: {LIST_DIALOG.primary_bg};
    color: {LIST_DIALOG.primary_color};
    border: none;
    border-radius: {GLOBAL.radius}px;
    padding: {LIST_DIALOG.btn_padding_v}px {LIST_DIALOG.btn_padding_h}px;
    min-width: {LIST_DIALOG.btn_min_width}px;
}}

QPushButton#{ButtonStyle.PERSONA}:hover {{
    background-color: {SETTINGS_DIALOG.btn_hover_bg};
}}

QPushButton#{ButtonStyle.PERSONA}:pressed {{
    background-color: {SETTINGS_DIALOG.btn_pressed_bg};
}}

QTextEdit#{ObjectName.PERSONA_PREVIEW} {{
    background-color: {SETTINGS_DIALOG.tab_bg};
}}"""

# 忙碌等待弹窗
WAIT_QSS = f"""\
QLabel#{ObjectName.WAIT_SPINNER} {{
    font-size: {WAIT_DIALOG.spinner_font_size}px;
    color: {WAIT_DIALOG.spinner_color};
}}"""


def with_dialog_base(*tail: str) -> Qss:
    """以基本、标题、主按钮三件打头拼装弹窗 QSS"""
    return Qss("\n".join([DIALOG_BASE_QSS, DIALOG_LABEL_QSS, DIALOG_BUTTON_QSS, *tail]))
