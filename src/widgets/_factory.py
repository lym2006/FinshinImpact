# src/widgets/_factory.py
"""控件构造工厂

- ButtonStyle 收口各窗按钮的 objectName，供各窗 QSS 选择器引用同名
- make_button 按样式名建按钮
- make_combo 按取值与文本灌下拉
"""

from collections.abc import Iterable
from enum import StrEnum

from PySide6.QtWidgets import QComboBox, QPushButton, QWidget


class ButtonStyle(StrEnum):
    """按钮视觉样式 objectName

    - 改名波及建钮处与各窗 QSS 选择器
    """

    PRIMARY = "btn_primary"
    SECONDARY = "btn_secondary"
    DANGER = "btn_danger"
    START = "btn_start"
    RESET = "btn_reset"
    PERSONA_OPEN = "btn_persona_open"
    PERSONA_PREVIEW = "btn_persona_preview"
    LIST_ADD = "btn_list_add"
    LIST_DEL = "btn_list_del"


def make_button(
    text: str, style: ButtonStyle, parent: QWidget | None = None
) -> QPushButton:
    """按样式名建一个按钮"""
    button = QPushButton(text, parent)
    button.setObjectName(style.value)
    return button


def make_combo(
    options: Iterable[tuple[object, str]], parent: QWidget | None = None
) -> QComboBox:
    """按取值与文本灌一个下拉框

    - 每项 addItem 存显示文本与取值
    """
    combo = QComboBox(parent)
    for value, text in options:
        combo.addItem(text, value)
    return combo
