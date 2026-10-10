# src/gui/dialogs/_wait.py
"""忙碌等待弹窗

- 模态转圈：动画由弹窗嵌套事件循环驱动，界面不僵死
- 后台结果到达后停圈显示，用户确认才关闭
- cancelable 模式：进行中允许取消，结果到达自动收窗
"""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from .._qss import build_wait_dialog_qss
from .._theme import GLOBAL, WAIT_DIALOG
from ._base import BaseDialog

# Qt 布局四边
_MARGIN_EDGES = 4  # setContentsMargins 收上下左右四个值


class WaitDialog(BaseDialog):
    """转圈等待 → 结果确认"""

    def __init__(
        self, text: str, parent: QWidget | None = None, cancelable: bool = False
    ) -> None:
        super().__init__(parent=parent, title=WAIT_DIALOG.title)
        self.set_always_on_top()
        self._cancelable = cancelable
        self._done = False
        self._idx = 0
        self._frames = WAIT_DIALOG.spinner_frames
        self.setStyleSheet(build_wait_dialog_qss())
        self.setFixedSize(WAIT_DIALOG.width, WAIT_DIALOG.height)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*[WAIT_DIALOG.pad] * _MARGIN_EDGES)
        layout.addStretch()
        row = QHBoxLayout()
        row.setSpacing(GLOBAL.radius)
        self._spinner = QLabel(self._frames[0])
        self._spinner.setObjectName("wait_spinner")
        self._label = QLabel(text)
        self._label.setWordWrap(True)
        row.addStretch()
        row.addWidget(self._spinner)
        row.addWidget(self._label)
        row.addStretch()
        layout.addLayout(row)
        layout.addStretch()
        self._btn = QPushButton(
            WAIT_DIALOG.cancel_text if cancelable else WAIT_DIALOG.ok_text
        )
        self._btn.setObjectName("btn_primary")

        # 可取消版进行中即亮按钮，一键语义随结果翻转
        if cancelable:
            self._btn.clicked.connect(self.reject)
        else:
            self._btn.clicked.connect(self.accept)
            self._btn.hide()
        layout.addWidget(self._btn, alignment=Qt.AlignmentFlag.AlignCenter)
        self.set_closable(cancelable)

        self._tick = QTimer(self)
        self._tick.setInterval(WAIT_DIALOG.tick_ms)
        self._tick.timeout.connect(self._advance)
        self._tick.start()

    def set_text(self, text: str) -> None:
        """更新等待文案

        - 倒计时刷新用
        """
        self._label.setText(text)

    def _advance(self) -> None:
        """播放下一帧"""
        self._idx = (self._idx + 1) % len(self._frames)
        self._spinner.setText(self._frames[self._idx])

    def finish(self, text: str, passed: bool = True) -> None:
        """等待窗收口

        - 停圈换文案
        - 可取消版结果即终态，自动收窗不再要确认
        - 重复调用只认首次
        """
        if self._done:
            return
        self._done = True
        self._tick.stop()
        self._spinner.setText(WAIT_DIALOG.ok_mark if passed else WAIT_DIALOG.fail_mark)
        self._label.setText(text)

        # 两行内用默认高，多出的行数按行高撑开防截断
        extra = max(0, text.count("\n") - 1) * WAIT_DIALOG.line_height
        self.setFixedSize(WAIT_DIALOG.width, WAIT_DIALOG.height + extra)

        if self._cancelable:
            # 结果即终态：收窗交给上层通知弹窗承载全文
            self.accept()
            return

        self._btn.show()
        self.set_closable(True)  # 结果已出，放行关闭

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        """关闭等待窗

        - 不可取消版结果未出前拒关，防后台线程失去宿主
        """
        if not self._cancelable and not self._done:
            event.ignore()
            return
        super().closeEvent(event)
