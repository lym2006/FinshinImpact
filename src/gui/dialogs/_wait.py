# src/gui/dialogs/_wait.py
"""忙碌等待弹窗（内部实现）

- 模态转圈：动画由弹窗嵌套事件循环驱动，界面不僵死
- 后台结果到达后停圈显示，用户确认才关闭
"""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from .._qss import build_wait_dialog_qss
from .._theme import GLOBAL
from .._theme import WAIT_DIALOG as PD
from ._base import BaseDialog


class WaitDialog(BaseDialog):
    """转圈等待 → 结果确认"""

    def __init__(self, text: str, parent=None) -> None:
        super().__init__(parent=parent, title=PD.title)
        self._done = False
        self._idx = 0
        self._frames = PD.spinner_frames
        self.setStyleSheet(build_wait_dialog_qss())
        self.setFixedSize(PD.width, PD.height)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*[PD.pad] * 4)
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
        self._btn = QPushButton(PD.ok_text)
        self._btn.setObjectName("btn_primary")
        self._btn.clicked.connect(self.accept)
        self._btn.hide()
        layout.addWidget(self._btn, alignment=Qt.AlignmentFlag.AlignCenter)
        self._tick = QTimer(self)
        self._tick.setInterval(PD.tick_ms)
        self._tick.timeout.connect(self._advance)
        self._tick.start()

    def set_text(self, text: str) -> None:
        """更新等待文案（倒计时刷新用）"""
        self._label.setText(text)

    # ==================== 动画与收尾 ====================

    def _advance(self) -> None:
        """播放下一帧"""
        self._idx = (self._idx + 1) % len(self._frames)
        self._spinner.setText(self._frames[self._idx])

    def finish(self, text: str, passed: bool = True) -> None:
        """出结果：停圈、换文案、亮按钮；重复调用只认首次"""
        if self._done:
            return
        self._done = True
        self._tick.stop()
        self._spinner.setText(PD.ok_mark if passed else PD.fail_mark)
        self._label.setText(text)
        self._btn.show()

    def closeEvent(self, event) -> None:  # noqa: N802
        """关闭等待窗

        结果未出之前拒绝关闭，防后台线程失去宿主。
        """
        if not self._done:
            event.ignore()
            return
        super().closeEvent(event)
