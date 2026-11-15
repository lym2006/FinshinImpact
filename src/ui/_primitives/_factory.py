"""控件构造工厂

- 按样式名建按钮
- 按取值与文本灌下拉
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


def fill_combo(combo: QComboBox, options: Iterable[tuple[object, str]]) -> None:
    """按取值与文本重灌一个下拉框的项

    - 每项 addItem 存显示文本与取值
    """
    combo.clear()
    for value, text in options:
        combo.addItem(text, value)


def make_combo(
    options: Iterable[tuple[object, str]], parent: QWidget | None = None
) -> QComboBox:
    """按取值与文本灌一个下拉框"""
    combo = QComboBox(parent)
    fill_combo(combo, options)
    return combo
