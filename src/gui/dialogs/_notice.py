# src/gui/dialogs/_notice.py
"""通用提示弹窗（内部实现）

- 单消息 + 确认按钮的家族化小窗
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from .._qss import build_notice_dialog_qss
from .._theme import NOTICE_DIALOG
from ._base import BaseDialog


class NoticeDialog(BaseDialog):
    """统一通知弹窗：提示/致命共用，critical 区分标题与确认语义"""

    def __init__(
        self, text: str, critical: bool = False, parent: QWidget | None = None
    ) -> None:
        super().__init__(
            parent=parent,
            title=NOTICE_DIALOG.fatal_title if critical else NOTICE_DIALOG.title,
        )
        self.set_always_on_top()
        self.setStyleSheet(build_notice_dialog_qss())

        extra = max(0, text.count("\n") - 1) * NOTICE_DIALOG.line_height
        self.setFixedSize(NOTICE_DIALOG.width, NOTICE_DIALOG.height + extra)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*[NOTICE_DIALOG.pad] * 4)
        layout.setSpacing(NOTICE_DIALOG.spacing)
        if critical:
            head = QLabel(NOTICE_DIALOG.fatal_head)
            head.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(head)
        label = QLabel(text)
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        layout.addStretch()
        btn = QPushButton(NOTICE_DIALOG.fatal_ok if critical else NOTICE_DIALOG.ok_text)
        btn.setObjectName("btn_primary")
        btn.clicked.connect(self.accept)
        btn.setDefault(True)
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)

    @staticmethod
    def notify(text: str, parent: QWidget | None = None) -> None:
        """模态展示一行提示"""
        NoticeDialog(text, parent=parent).exec()
