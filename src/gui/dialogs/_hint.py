# src/gui/dialogs/_hint.py
"""通用提示弹窗（内部实现）

- 单消息 + 确认按钮的家族化小窗
- 替代原生 QMessageBox，保持配色圆角统一
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout

from .._qss import build_hint_dialog_qss
from .._theme import HINT_DIALOG as PD
from ._base import BaseDialog


class HintDialog(BaseDialog):
    """一句话提示，点"知道了"关闭"""

    def __init__(self, text: str, parent=None) -> None:
        super().__init__(parent=parent, title=PD.title)
        self.setStyleSheet(build_hint_dialog_qss())
        self.setFixedSize(PD.width, PD.height)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(*[PD.pad] * 4)
        layout.setSpacing(PD.spacing)

        label = QLabel(text)
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        layout.addStretch()

        btn = QPushButton(PD.ok_text)
        btn.setObjectName("btn_primary")
        btn.clicked.connect(self.accept)
        btn.setDefault(True)
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)

    @staticmethod
    def notify(text: str, parent=None) -> None:
        """模态展示一行提示"""
        HintDialog(text, parent=parent).exec()
