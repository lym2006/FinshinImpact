# src/ui/_dialogs/_shutdown.py
"""关闭确认弹窗

- 提供退出进度反馈，防强杀泄漏
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from skin.qss import build_shutdown_dialog_qss
from skin.theme import SHUTDOWN_DIALOG, ButtonStyle

from .._primitives import make_button
from ._base import BaseDialog

# Qt 布局四边
_MARGIN_EDGES = 4  # setContentsMargins 收上下左右四个值


class ShutdownDialog(BaseDialog):
    """退出提示弹窗"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent, title=SHUTDOWN_DIALOG.title)
        self.set_always_on_top()

        # 固定大小（顶层窗尺寸 QSS 压不过布局，只能在这钉）
        self.setFixedSize(SHUTDOWN_DIALOG.width, SHUTDOWN_DIALOG.height)

        self.setStyleSheet(build_shutdown_dialog_qss())

        layout = QVBoxLayout(self)  # 布局与间距
        layout.setContentsMargins(*([SHUTDOWN_DIALOG.padding] * _MARGIN_EDGES))
        layout.setSpacing(SHUTDOWN_DIALOG.spacing)

        # 提示文字
        self._label = QLabel(SHUTDOWN_DIALOG.message)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setFont(QFont(SHUTDOWN_DIALOG.font_name, SHUTDOWN_DIALOG.font_size))
        layout.addWidget(self._label)
        btn_layout = QHBoxLayout()  # 按钮区
        btn_layout.addStretch()

        # 取消按钮
        self._cancel_btn = make_button(
            SHUTDOWN_DIALOG.cancel_text, ButtonStyle.SECONDARY
        )
        self._cancel_btn.clicked.connect(self.reject)

        # 确认按钮
        self._confirm_btn = make_button(
            SHUTDOWN_DIALOG.confirm_text, ButtonStyle.DANGER
        )
        self._confirm_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self._cancel_btn)
        btn_layout.addWidget(self._confirm_btn)
        layout.addLayout(btn_layout)

        # 默认焦点放在取消按钮上（防误触）
        self._cancel_btn.setFocus()
