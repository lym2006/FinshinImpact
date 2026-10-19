# src/gui/dialogs/_shutdown.py
"""关闭确认弹窗（内部实现）

- 提供退出进度反馈，防强杀泄漏
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from .._theme import GLOBAL
from .._theme import SHUTDOWN_DIALOG as DIALOG
from ._base import BaseDialog


class ShutdownDialog(BaseDialog):
    """退出提示弹窗"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent=parent, title="关闭确认")

        # 固定大小
        self.setFixedSize(DIALOG.width, DIALOG.height)

        self.setStyleSheet(  # 设置背景色
            f"QDialog {{ background-color: {DIALOG.bg_color}; }}",
        )

        layout = QVBoxLayout(self)  # 布局与间距
        layout.setContentsMargins(*([DIALOG.padding] * 4))
        layout.setSpacing(DIALOG.spacing)

        # 提示文字
        self._label = QLabel(DIALOG.message)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setStyleSheet(f"color: {DIALOG.text_color};")
        self._label.setFont(QFont(DIALOG.font_name, DIALOG.font_size))
        layout.addWidget(self._label)
        btn_layout = QHBoxLayout()  # 按钮区
        btn_layout.addStretch()

        # 取消按钮
        self._cancel_btn = QPushButton(DIALOG.cancel_text)
        self._cancel_btn.setFixedSize(DIALOG.btn_width, DIALOG.btn_height)
        self._cancel_btn.setStyleSheet(
            f"QPushButton {{ background-color: {DIALOG.cancel_bg}; "
            f"color: {DIALOG.cancel_color}; border-radius: {GLOBAL.radius}px; }}"
        )
        self._cancel_btn.clicked.connect(self.reject)

        # 确认按钮
        self._confirm_btn = QPushButton(DIALOG.confirm_text)
        self._confirm_btn.setFixedSize(DIALOG.btn_width, DIALOG.btn_height)
        self._confirm_btn.setStyleSheet(
            f"QPushButton {{ background-color: {DIALOG.confirm_bg}; "
            f"color: {DIALOG.confirm_color}; border-radius: {GLOBAL.radius}px; }}"
        )
        self._confirm_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self._cancel_btn)
        btn_layout.addWidget(self._confirm_btn)
        layout.addLayout(btn_layout)

        # 默认焦点放在取消按钮上（防误触）
        self._cancel_btn.setFocus()
