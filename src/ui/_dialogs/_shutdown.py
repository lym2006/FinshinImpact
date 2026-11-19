"""关闭确认弹窗

- 退出前先问一句，只留取消与确认两颗钮
- 询问期间锁住所有窗，默认焦点放在取消
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from skin.qss import build_shutdown_dialog_qss
from skin.theme import SHUTDOWN_DIALOG, ButtonStyle

from .._primitives import BaseDialog, make_button, set_margins


class ShutdownDialog(BaseDialog):
    """退出提示弹窗"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent, title=SHUTDOWN_DIALOG.title)

        # 退出是全程序的事，这一只仍锁住所有窗
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        # 固定大小（顶层窗尺寸 QSS 压不过布局，只能在这钉）
        self.setFixedSize(SHUTDOWN_DIALOG.width, SHUTDOWN_DIALOG.height)

        self.setStyleSheet(build_shutdown_dialog_qss())

        layout = QVBoxLayout(self)  # 布局与间距
        set_margins(layout, SHUTDOWN_DIALOG.padding)
        layout.setSpacing(SHUTDOWN_DIALOG.spacing)

        self._label = QLabel(SHUTDOWN_DIALOG.message)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setFont(QFont(SHUTDOWN_DIALOG.font_name, SHUTDOWN_DIALOG.font_size))
        layout.addWidget(self._label)
        btn_layout = QHBoxLayout()  # 按钮区
        btn_layout.addStretch()

        self._cancel_btn = make_button(SHUTDOWN_DIALOG.cancel_text, ButtonStyle.NEUTRAL)
        self._cancel_btn.clicked.connect(self.reject)

        self._confirm_btn = make_button(
            SHUTDOWN_DIALOG.confirm_text, ButtonStyle.DANGER
        )
        self._confirm_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self._cancel_btn)
        btn_layout.addWidget(self._confirm_btn)
        layout.addLayout(btn_layout)

        # 默认焦点放在取消按钮上（防误触）
        self._cancel_btn.setFocus()
