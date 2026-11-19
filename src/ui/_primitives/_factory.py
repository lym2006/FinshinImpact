"""控件构造工厂

- 按用途词与尺寸档建按钮，objectName 由词表统一拼
- 按取值与文本灌下拉
"""

from collections.abc import Callable, Iterable

from PySide6.QtWidgets import QComboBox, QPushButton, QWidget

from skin.theme import ButtonSize, ButtonStyle, button_object_name


def make_button(
    text: str,
    style: ButtonStyle,
    parent: QWidget | None = None,
    *,
    size: ButtonSize = ButtonSize.STANDARD,
    on_click: Callable[[], None] | None = None,
    default: bool = False,
) -> QPushButton:
    """按用途词与尺寸档建一个按钮"""
    button = QPushButton(text, parent)
    button.setObjectName(button_object_name(style, size))
    if on_click is not None:
        button.clicked.connect(on_click)
    if default:
        button.setDefault(True)
    return button


def fill_combo(combo: QComboBox, options: Iterable[tuple[object, str]]) -> None:
    """按取值与文本重灌一个下拉框的项

    - 每项存显示文本与取值
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
