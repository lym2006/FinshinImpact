"""人设正文入口

- 面板给预览、编辑与按文件重载三个入口
- 预览只读生效正文，编辑与重载都交拍板窗
"""

from typing import TypeAlias

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from skin.qss import build_settings_dialog_qss
from skin.theme import SETTINGS_DIALOG, ButtonSize, ButtonStyle, ObjectName
from utils.persona import applied_persona_text, inject_owner, read_persona_file

from ..._primitives import BaseDialog, make_button, set_margins
from .._notice import NoticeDialog
from ._edit import PersonaEditorDialog
from ._resolve import PersonaResolveDialog

# 人设字符串被用户改成单行时渲染控件会回落 QLineEdit
_TextWidget: TypeAlias = QTextEdit | QLineEdit


def _text_of(widget: _TextWidget) -> str:
    """取文本控件当前值"""
    if isinstance(widget, QTextEdit):
        return widget.toPlainText()
    return widget.text()


class _PersonaPreviewDialog(BaseDialog):
    """人设正文预览

    - 正文取生效正文并按 markdown 渲染
    """

    def __init__(self, owner_id: str, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent, title=SETTINGS_DIALOG.persona_title)
        self.setStyleSheet(build_settings_dialog_qss())

        layout = QVBoxLayout(self)
        set_margins(layout, SETTINGS_DIALOG.input_padding_h)
        layout.setSpacing(SETTINGS_DIALOG.desc_spacing)

        body = QTextEdit()
        body.setObjectName(ObjectName.PERSONA_PREVIEW)
        body.setReadOnly(True)

        # 最小尺寸即默认尺寸，窗口拉大时正文框随布局弹性填满
        body.setMinimumSize(
            SETTINGS_DIALOG.persona_preview_width,
            SETTINGS_DIALOG.persona_preview_height,
        )
        body.setMarkdown(inject_owner(applied_persona_text(), owner_id))
        layout.addWidget(body, stretch=1)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_close = make_button(
            SETTINGS_DIALOG.persona_close_text, ButtonStyle.OUTLINE, default=True
        )
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)


class PersonaPreviewRow(QWidget):
    """人设正文入口行

    - 标题在上，三颗入口在下一排
    - 预览与编辑各开一窗
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._owner: _TextWidget | None = None

        layout = QVBoxLayout(self)
        set_margins(layout, SETTINGS_DIALOG.margin)
        layout.setSpacing(SETTINGS_DIALOG.desc_spacing)

        title = QLabel(SETTINGS_DIALOG.persona_label)
        title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        btn_preview = make_button(
            SETTINGS_DIALOG.persona_preview_text,
            ButtonStyle.PRIMARY,
            size=ButtonSize.SMALL,
        )
        btn_preview.clicked.connect(self._on_preview_clicked)

        btn_edit = make_button(
            SETTINGS_DIALOG.persona_edit_text,
            ButtonStyle.PRIMARY,
            size=ButtonSize.SMALL,
        )
        btn_edit.clicked.connect(self._on_edit_clicked)

        btn_reload = make_button(
            SETTINGS_DIALOG.persona_reload_text,
            ButtonStyle.PRIMARY,
            size=ButtonSize.SMALL,
        )
        btn_reload.clicked.connect(self._on_reload_clicked)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(SETTINGS_DIALOG.desc_spacing)
        btn_layout.addWidget(btn_preview)
        btn_layout.addWidget(btn_edit)
        btn_layout.addWidget(btn_reload)
        btn_layout.addStretch()

        layout.addWidget(title)
        layout.addLayout(btn_layout)

    def bind(self, owner: QWidget) -> bool:
        """绑定主人输入行

        - 控件类型不符返回 False，由调用方放弃挂载
        """
        if not isinstance(owner, (QTextEdit, QLineEdit)):
            return False
        self._owner = owner
        return True

    def _on_preview_clicked(self) -> None:
        """弹窗渲染生效正文"""
        if self._owner is None:
            return
        owner_id = _text_of(self._owner).strip()
        _PersonaPreviewDialog(owner_id, parent=self.window()).exec()

    def _on_edit_clicked(self) -> None:
        """编辑正文后交拍板窗"""
        applied = applied_persona_text()
        edited = PersonaEditorDialog.edit(applied, parent=self.window())
        if edited is None:
            return
        PersonaResolveDialog.resolve(
            applied,
            edited,
            SETTINGS_DIALOG.persona_label_active,
            SETTINGS_DIALOG.persona_label_edited,
            parent=self.window(),
        )

    def _on_reload_clicked(self) -> None:
        """现读实例文件那份交拍板窗

        - 读不出只提示，两份一致由拍板窗统一提示
        """
        parent = self.window()
        disk = read_persona_file()
        if disk is None:
            NoticeDialog.notify(SETTINGS_DIALOG.persona_file_read_fail, parent=parent)
            return
        PersonaResolveDialog.resolve(
            applied_persona_text(),
            disk,
            SETTINGS_DIALOG.persona_label_active,
            SETTINGS_DIALOG.persona_label_file,
            parent=parent,
        )
