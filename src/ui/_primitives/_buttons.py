"""按钮装配件

- ButtonSpec 记一颗按钮的文案、用途词、尺寸档、回调与默认态
- ButtonBar 把一排 spec 建出来并按靠左或靠右摆放
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget

from skin.theme import ButtonSize, ButtonStyle

from ._factory import make_button


@dataclass(frozen=True)
class ButtonSpec:
    """一颗按钮的装配参数"""

    text: str
    style: ButtonStyle
    size: ButtonSize = ButtonSize.STANDARD
    on_click: Callable[[], None] | None = None
    default: bool = False


class ButtonBar(QWidget):
    """一排按钮

    - 默认靠右，可改靠左
    - buttons 按 spec 顺序给出建成后的按钮
    """

    def __init__(
        self,
        specs: Sequence[ButtonSpec],
        parent: QWidget | None = None,
        *,
        align_left: bool = False,
        spacing: int | None = None,
    ) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        if spacing is not None:
            layout.setSpacing(spacing)
        self._buttons = [
            make_button(
                spec.text,
                spec.style,
                self,
                size=spec.size,
                on_click=spec.on_click,
                default=spec.default,
            )
            for spec in specs
        ]
        if not align_left:
            layout.addStretch()
        for button in self._buttons:
            layout.addWidget(button)
        if align_left:
            layout.addStretch()

    @property
    def buttons(self) -> list[QPushButton]:
        """按 spec 顺序排好的按钮"""
        return list(self._buttons)
