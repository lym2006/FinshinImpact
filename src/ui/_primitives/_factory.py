# src/ui/_primitives/_factory.py
"""控件构造工厂

- make_button 按样式名建按钮
- make_combo 按取值与文本灌下拉
"""

from collections.abc import Iterable

from PySide6.QtWidgets import QComboBox, QPushButton, QWidget

from skin.theme import ButtonStyle


def make_button(
    text: str, style: ButtonStyle, parent: QWidget | None = None
) -> QPushButton:
    """按样式名建一个按钮"""
    button = QPushButton(text, parent)
    button.setObjectName(style)
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
