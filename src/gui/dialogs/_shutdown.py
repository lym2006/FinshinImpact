# src/gui/dialogs/_shutdown.py
"""关闭确认弹窗（内部实现）

- 提供退出进度反馈，防强杀泄漏
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from .._theme import GLOBAL, SHUTDOWN_DIALOG
from ._base import BaseDialog


class ShutdownDialog(BaseDialog):
    """退出提示弹窗"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent, title=SHUTDOWN_DIALOG.title)
        self.set_always_on_top()

        # 固定大小
        self.setFixedSize(SHUTDOWN_DIALOG.width, SHUTDOWN_DIALOG.height)

        self.setStyleSheet(  # 设置背景色
            f"QDialog {{ background-color: {SHUTDOWN_DIALOG.bg_color}; }}",
        )

        layout = QVBoxLayout(self)  # 布局与间距
        layout.setContentsMargins(*([SHUTDOWN_DIALOG.padding] * 4))
        layout.setSpacing(SHUTDOWN_DIALOG.spacing)

        # 提示文字
        self._label = QLabel(SHUTDOWN_DIALOG.message)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setStyleSheet(f"color: {SHUTDOWN_DIALOG.text_color};")
        self._label.setFont(QFont(SHUTDOWN_DIALOG.font_name, SHUTDOWN_DIALOG.font_size))
        layout.addWidget(self._label)
        btn_layout = QHBoxLayout()  # 按钮区
        btn_layout.addStretch()

        # 取消按钮
        self._cancel_btn = QPushButton(SHUTDOWN_DIALOG.cancel_text)
        self._cancel_btn.setFixedSize(
            SHUTDOWN_DIALOG.btn_width, SHUTDOWN_DIALOG.btn_height
        )
        self._cancel_btn.setStyleSheet(
            f"QPushButton {{ background-color: {SHUTDOWN_DIALOG.cancel_bg}; "
            f"color: {SHUTDOWN_DIALOG.cancel_color}; border-radius: {GLOBAL.radius}px; }}"
        )
        self._cancel_btn.clicked.connect(self.reject)

        # 确认按钮
        self._confirm_btn = QPushButton(SHUTDOWN_DIALOG.confirm_text)
        self._confirm_btn.setFixedSize(
            SHUTDOWN_DIALOG.btn_width, SHUTDOWN_DIALOG.btn_height
        )
        self._confirm_btn.setStyleSheet(
            f"QPushButton {{ background-color: {SHUTDOWN_DIALOG.confirm_bg}; "
            f"color: {SHUTDOWN_DIALOG.confirm_color}; border-radius: {GLOBAL.radius}px; }}"
        )
        self._confirm_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self._cancel_btn)
        btn_layout.addWidget(self._confirm_btn)
        layout.addLayout(btn_layout)

        # 默认焦点放在取消按钮上（防误触）
        self._cancel_btn.setFocus()
