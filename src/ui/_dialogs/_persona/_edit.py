"""人设正文编辑窗

- 正文按原文展示，主人 id 留占位符
- 确认交出待生效正文，「用内置模板覆盖」直接开拍板窗
"""

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from skin.qss import build_settings_dialog_qss
from skin.theme import SETTINGS_DIALOG, ButtonStyle, ObjectName
from utils.persona import applied_persona_text, read_template_text

from ..._primitives import BaseDialog, ButtonBar, ButtonSpec, set_margins
from .._notice import NoticeDialog
from ._resolve import PersonaResolveDialog


class PersonaEditorDialog(BaseDialog):
    """人设正文编辑器

    - 正文按原文展示，主人 id 留占位符
    - 确认交出内容，定稿与清历史归拍板窗
    """

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent, title=SETTINGS_DIALOG.persona_editor_title)
        self.setStyleSheet(build_settings_dialog_qss())

        layout = QVBoxLayout(self)
        set_margins(layout, SETTINGS_DIALOG.input_padding_h)
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
        left_bar = ButtonBar(
            [
                ButtonSpec(
                    SETTINGS_DIALOG.persona_use_template,
                    ButtonStyle.DANGER,
                    on_click=self._on_use_template,
                )
            ],
            self,
            align_left=True,
        )
        btn_layout.addWidget(left_bar)
        right_bar = self.install_button_bar(
            btn_layout,
            [
                ButtonSpec(
                    SETTINGS_DIALOG.cancel_text,
                    ButtonStyle.OUTLINE,
                    on_click=self.reject,
                ),
                ButtonSpec(
                    SETTINGS_DIALOG.confirm_text,
                    ButtonStyle.PRIMARY,
                    on_click=self.accept,
                    default=True,
                ),
            ],
        )
        btn_layout.setStretchFactor(right_bar, 1)
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

        - 读不出模板只提示，一个字不改
        - 有差异时先收起本窗再开拍板窗
        """
        template = read_template_text()
        if not template:
            NoticeDialog.notify(SETTINGS_DIALOG.persona_no_template, parent=self)
            return
        applied = applied_persona_text()
        parent = self.parentWidget()
        self.reject()
        PersonaResolveDialog.resolve(
            applied,
            template,
            SETTINGS_DIALOG.persona_label_active,
            SETTINGS_DIALOG.persona_label_template,
            parent=parent,
        )
