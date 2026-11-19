"""弹窗基类

- 统一「只锁调出它的窗」的共有窗口行为
- 窗每次显示打一行调试日志，引导期没有实例路径就不写
- 底排按 spec 列表装配，按钮形状仍由工厂与词表决定
"""

from collections.abc import Sequence

from PySide6.QtCore import Qt
from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import QDialog, QLayout, QWidget

from system.profile_env import get_profile

from ._buttons import ButtonBar, ButtonSpec


def _log_shown(title: str, kind: str) -> None:
    """日志文件挂在实例目录下，身份码落定前无处可写"""
    if not get_profile():
        return
    from utils import get_logger

    get_logger("GUI.Dialog").debug(f"窗已显示 {title}（{kind}）")


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
        _log_shown(self.windowTitle() or "无题", type(self).__name__)

    def set_closable(self, closable: bool) -> None:
        """切换标题栏关闭按钮可用态

        - 置灰态无悬停与按下反馈，防用户误以为可点
        - 重设后按原位置重新显示
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

    def install_button_bar(
        self,
        layout: QLayout,
        specs: Sequence[ButtonSpec],
        *,
        align_left: bool = False,
    ) -> ButtonBar:
        """在给定布局里装一排按钮"""
        bar = ButtonBar(specs, self, align_left=align_left)
        layout.addWidget(bar)
        return bar
