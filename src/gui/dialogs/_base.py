# src/gui/dialogs/_base.py
"""弹窗基类

- 定义弹窗共有样式与逻辑
- 实现全局主题统一应用
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QWidget


class BaseDialog(QDialog):
    """所有自定义弹窗的基类"""

    def __init__(self, parent: QWidget | None = None, title: str = "") -> None:
        super().__init__(parent=parent)

        self.setWindowTitle(title)  # 基础窗口属性
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

    def set_always_on_top(self) -> None:
        """置顶模态框

        - 压过同样置顶的检测窗，杜绝隐形模态锁死输入
        - 改 flag 会重建原生窗口，只允许首显前调用，终身不碰
        """
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)

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
