# src/ui/_dialogs/_base.py
"""弹窗基类

- 统一「只锁调出它的窗」的共有窗口行为
- 窗显示出来即记一行，供对着按钮那行查窗没弹出来
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import QDialog, QWidget

from utils.logger import get_logger

_logger = get_logger("GUI.Dialog")


class BaseDialog(QDialog):
    """所有自定义弹窗的基类"""

    RESULT_WINDOW = False  # 契约声明：报结果的窗改 True，同场只出现一只

    def __init__(self, parent: QWidget | None = None, title: str = "") -> None:
        super().__init__(parent=parent)

        self.setWindowTitle(title)
        self.setWindowModality(Qt.WindowModality.WindowModal)

    def showEvent(self, event: QShowEvent) -> None:  # noqa: N802
        """记下窗真正显示出来的那一刻"""
        super().showEvent(event)
        title = self.windowTitle() or "无题"
        _logger.debug(f"窗已显示 {title}（{type(self).__name__}）")

    def set_closable(self, closable: bool) -> None:
        """切换标题栏关闭按钮可用态

        - 置灰态无悬停与按下反馈，防用户误以为可点
        - 改 flag 会重建原生窗口，需原位重新显示
        """
        flags = self.windowFlags()
        flags |= Qt.WindowType.WindowCloseButtonHint
        if not closable:
            flags &= ~Qt.WindowType.WindowCloseButtonHint
        was_visible = self.isVisible()
        pos = self.pos()
        self.setWindowFlags(flags)
        if was_visible:
            self.move(pos)
            self.show()
