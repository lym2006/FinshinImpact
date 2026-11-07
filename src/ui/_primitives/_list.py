# src/ui/_primitives/_list.py
"""通用列表行为件

- 在 QListWidget 之上加选中联动与删除当前行的公共操作
- 竖向按像素滚，滚轮一轮挪一小截
"""

from collections.abc import Iterable

from PySide6.QtWidgets import QAbstractItemView, QListWidget, QWidget

from skin.theme import SCROLLBAR


class ThemedList(QListWidget):
    """带选中联动与增删操作的列表"""

    def __init__(self, parent: QWidget | None = None) -> None:
        """竖向滚动按公共档位走像素"""
        super().__init__(parent)
        self.set_fine_scroll(SCROLLBAR.step)

    def set_fine_scroll(self, step: int) -> None:
        """设定滚轮一轮挪几像素

        - 滚轮挪的量是这一格乘 Qt 每轮的三格
        - 按整行走的话一轮即跨三行，长清单一下刷过去
        """
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.verticalScrollBar().setSingleStep(step)

    def enable_on_selection(self, buttons: Iterable[QWidget]) -> None:
        """按选中态联动这批控件可用性

        - 接线时先按当前选中回填一次初值
        """
        targets = tuple(buttons)

        def sync(*_: object) -> None:
            enabled = self.currentItem() is not None
            for button in targets:
                button.setEnabled(enabled)

        self.currentItemChanged.connect(sync)
        sync()

    def remove_current(self) -> None:
        """删除当前选中行

        - 无选中行即跳过
        """
        row = self.currentRow()
        if row >= 0:
            self.takeItem(row)
