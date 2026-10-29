# src/ui/_dialogs/_settings/_persona_edit.py
"""人设正文编辑窗

- 正文按原文展示，主人 id 留占位符
- 确认交出待生效正文，「用模板覆盖」直接开拍板窗
"""

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from skin.qss import build_settings_dialog_qss
from skin.theme import SETTINGS_DIALOG, ButtonStyle, ObjectName
from utils.persona import applied_persona_text, read_template_text

from ..._primitives import make_button
from .._base import BaseDialog
from .._notice import NoticeDialog
from ._persona_resolve import PersonaResolveDialog

_MARGIN_EDGES = 4  # setContentsMargins 收上下左右四个值


class PersonaEditorDialog(BaseDialog):
    """人设正文编辑器

    - 正文按原文展示，主人 id 留占位符
    - 确认交出内容，定稿与清历史归拍板窗
    """

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent, title=SETTINGS_DIALOG.persona_editor_title)
        self.set_always_on_top()
        self.setStyleSheet(build_settings_dialog_qss())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(*[SETTINGS_DIALOG.input_padding_h] * _MARGIN_EDGES)
        layout.setSpacing(SETTINGS_DIALOG.desc_spacing)

        body = QTextEdit()
        body.setObjectName(ObjectName.PERSONA_PREVIEW)
        body.setMinimumSize(
            SETTINGS_DIALOG.persona_preview_width,
            SETTINGS_DIALOG.persona_editor_height,
        )
        body.setPlainText(text)
        layout.addWidget(body, stretch=1)

        tip = QLabel(SETTINGS_DIALOG.persona_editor_tip)
        tip.setWordWrap(True)
        layout.addWidget(tip)

        btn_layout = QHBoxLayout()
        btn_template = make_button(
            SETTINGS_DIALOG.persona_use_template, ButtonStyle.DANGER
        )
        btn_template.clicked.connect(self._on_use_template)
        btn_cancel = QPushButton(SETTINGS_DIALOG.cancel_text)
        btn_cancel.clicked.connect(self.reject)
        btn_ok = make_button(SETTINGS_DIALOG.confirm_text, ButtonStyle.PRIMARY)
        btn_ok.clicked.connect(self.accept)
        btn_ok.setDefault(True)
        btn_layout.addWidget(btn_template)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_ok)
        layout.addLayout(btn_layout)

        self._body = body

    @staticmethod
    def edit(text: str, parent: QWidget | None = None) -> str | None:
        """模态展示并取回待生效正文

        - 取消返回 None
        """
        dialog = PersonaEditorDialog(text, parent=parent)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return None
        return dialog._body.toPlainText()

    def _on_use_template(self) -> None:
        """用内置模板替换正文

        - 读不出模板与内容一致都只提示，一个字不改
        - 有差异开拍板窗，定稿后本窗收起
        """
        template = read_template_text()
        if not template:
            NoticeDialog.notify(SETTINGS_DIALOG.persona_no_template, parent=self)
            return
        applied = applied_persona_text()
        if template == applied:
            NoticeDialog.notify(SETTINGS_DIALOG.persona_template_same, parent=self)
            return
        parent = self.parentWidget()
        self.reject()
        PersonaResolveDialog.resolve(
            applied,
            template,
            SETTINGS_DIALOG.persona_label_active,
            SETTINGS_DIALOG.persona_label_template,
            SETTINGS_DIALOG.persona_source_template,
            parent=parent,
        )
