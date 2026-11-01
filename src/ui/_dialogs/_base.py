# src/ui/_dialogs/_base.py
"""弹窗基类

- 统一「只锁调出它的窗」的共有窗口行为
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QWidget


class BaseDialog(QDialog):
    """所有自定义弹窗的基类"""

    RESULT_WINDOW = False  # 契约声明：报结果的窗改 True，同场只出现一只

    def __init__(self, parent: QWidget | None = None, title: str = "") -> None:
        super().__init__(parent=parent)

        self.setWindowTitle(title)  # 基础窗口属性
        self.setWindowModality(Qt.WindowModality.WindowModal)

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
