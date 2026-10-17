# src/widgets/_list.py
"""通用列表行为件

- 在 QListWidget 之上加选中联动与删除当前行的公共操作
"""

from collections.abc import Iterable

from PySide6.QtWidgets import QListWidget, QWidget


class ThemedList(QListWidget):
    """带选中联动与增删操作的列表"""

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
