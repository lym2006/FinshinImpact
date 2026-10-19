# src/gui/dialogs/_fatal.py
"""致命错误弹窗（内部实现）

- 提供致命错误展示与退出确认
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from .._qss import build_settings_dialog_qss
from .._theme import FATAL_DIALOG as FATAL
from ._base import BaseDialog


class FatalDialog(BaseDialog):
    """致命错误提示弹窗"""

    def __init__(self, message: str, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent, title="致命错误")
        self.setStyleSheet(build_settings_dialog_qss())
        self.setFixedSize(FATAL.width, FATAL.height)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*[FATAL.padding] * 4)
        layout.setSpacing(FATAL.spacing)
        title = QLabel(FATAL.title)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        detail = QLabel(message)
        detail.setWordWrap(True)
        detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(detail)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_ok = QPushButton(FATAL.confirm_text)
        btn_ok.setObjectName("btn_primary")
        btn_ok.clicked.connect(self.accept)
        btn_ok.setDefault(True)  # Enter 即确认，免鼠标
        btn_layout.addWidget(btn_ok)
        layout.addLayout(btn_layout)
