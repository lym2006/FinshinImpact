# src/ui/_dialogs/_persona/_sync.py
"""默认人设更新弹窗

- 提示内置默认人设有更新，并给出一键覆盖实例副本的入口
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from skin.qss import build_notice_dialog_qss
from skin.theme import NOTICE_DIALOG, ButtonStyle
from utils.init_files import apply_persona_template, mark_persona_prompted

from ..._primitives import make_button
from .._base import BaseDialog
from .._notice import NoticeDialog

# Qt 布局四边
_MARGIN_EDGES = 4  # setContentsMargins 收上下左右四个值


class PersonaSyncDialog(BaseDialog):
    """默认人设更新提示弹窗

    - 覆盖副本由按钮当场授权，点确认才改写并回报结果
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent, title=NOTICE_DIALOG.persona_title)
        self.set_always_on_top()
        self.setStyleSheet(build_notice_dialog_qss())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(*[NOTICE_DIALOG.pad] * _MARGIN_EDGES)
        layout.setSpacing(NOTICE_DIALOG.spacing)
        tip = QLabel(NOTICE_DIALOG.persona_text)
        tip.setWordWrap(True)
        tip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(tip)
        layout.addStretch()
        layout.addLayout(self._make_buttons())

        self.setFixedWidth(NOTICE_DIALOG.width)
        height = max(NOTICE_DIALOG.height, layout.sizeHint().height())
        self.setFixedHeight(height)

    @staticmethod
    def notify_update(parent: QWidget | None = None) -> None:
        """模态展示人设更新提示

        - 关窗即记本版已提示，保留原样与关窗同义
        """
        dialog = PersonaSyncDialog(parent=parent)
        dialog.raise_()
        dialog.activateWindow()
        accepted = dialog.exec() == dialog.DialogCode.Accepted
        mark_persona_prompted()
        if not accepted:
            return
        detail = (
            NOTICE_DIALOG.persona_applied
            if apply_persona_template()
            else NOTICE_DIALOG.persona_apply_fail
        )
        NoticeDialog.notify(detail, parent=parent)

    def _make_buttons(self) -> QHBoxLayout:
        """保留我的人设 / 用内置模板覆盖"""
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_keep = QPushButton(NOTICE_DIALOG.persona_keep_text)
        btn_keep.clicked.connect(self.reject)
        btn_apply = make_button(NOTICE_DIALOG.persona_apply_text, ButtonStyle.PRIMARY)
        btn_apply.clicked.connect(self.accept)
        btn_apply.setDefault(True)
        btn_layout.addWidget(btn_keep)
        btn_layout.addWidget(btn_apply)
        return btn_layout
