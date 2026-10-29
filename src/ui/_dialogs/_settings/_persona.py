# src/ui/_dialogs/_settings/_persona.py
"""人设正文入口

- 面板给预览、编辑与从文件重新加载三个入口
- 预览纯读生效正文，编辑确认与重载都当场落盘
- 重载按钮是面板里唯一读实例文件的地方
"""

from typing import TypeAlias

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from skin.qss import build_settings_dialog_qss
from skin.theme import SETTINGS_DIALOG, ButtonStyle, ObjectName
from utils.persona import applied_persona_text, inject_owner, read_persona_file

from ..._primitives import make_button
from .._base import BaseDialog
from .._notice import NoticeDialog
from ._persona_edit import PersonaEditorDialog
from ._persona_resolve import PersonaResolveDialog

# 人设字符串被用户改成单行时渲染控件会回落 QLineEdit
_TextWidget: TypeAlias = QTextEdit | QLineEdit

# Qt 布局四边
_MARGIN_EDGES = 4  # setContentsMargins 收上下左右四个值


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
        self.set_always_on_top()
        self.setStyleSheet(build_settings_dialog_qss())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(*[SETTINGS_DIALOG.input_padding_h] * _MARGIN_EDGES)
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
        btn_close = QPushButton(SETTINGS_DIALOG.persona_close_text)
        btn_close.clicked.connect(self.accept)
        btn_close.setDefault(True)
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)


class PersonaPreviewRow(QWidget):
    """人设正文入口行

    - 标签占位与字段行同宽，按钮才与其他输入框左对齐
    - 预览与编辑各开一窗
    """

    def __init__(self, label_width: int = 0, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._owner: _TextWidget | None = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(*[SETTINGS_DIALOG.margin] * _MARGIN_EDGES)
        layout.setSpacing(SETTINGS_DIALOG.desc_spacing)

        title = QLabel(SETTINGS_DIALOG.persona_label)
        title.setMinimumWidth(label_width)

        btn_preview = make_button(
            SETTINGS_DIALOG.persona_preview_text, ButtonStyle.PERSONA
        )
        btn_preview.clicked.connect(self._on_preview_clicked)

        btn_edit = make_button(SETTINGS_DIALOG.persona_edit_text, ButtonStyle.PERSONA)
        btn_edit.clicked.connect(self._on_edit_clicked)

        btn_reload = make_button(
            SETTINGS_DIALOG.persona_reload_text, ButtonStyle.PERSONA
        )
        btn_reload.clicked.connect(self._on_reload_clicked)

        # 本行内容顶部对齐，不与上方多行输入框的底边缠斗
        layout.addWidget(title)
        layout.addWidget(btn_preview, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addWidget(btn_edit, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addWidget(btn_reload, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addStretch()

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
        """编辑正文，确认即开拍板窗当场落盘"""
        applied = applied_persona_text()
        edited = PersonaEditorDialog.edit(applied, parent=self.window())
        if edited is None:
            return
        PersonaResolveDialog.resolve(
            applied,
            edited,
            SETTINGS_DIALOG.persona_label_active,
            SETTINGS_DIALOG.persona_label_edited,
            SETTINGS_DIALOG.persona_source_panel,
            parent=self.window(),
        )

    def _on_reload_clicked(self) -> None:
        """比对实例文件与当前正文，按所选当场落盘

        - 读文件与比对都收在这一颗按钮，一致只提示一句
        """
        parent = self.window()
        disk = read_persona_file()
        if disk is None:
            NoticeDialog.notify(SETTINGS_DIALOG.persona_file_read_fail, parent=parent)
            return
        applied = applied_persona_text()
        if disk == applied:
            NoticeDialog.notify(SETTINGS_DIALOG.persona_reload_same, parent=parent)
            return
        PersonaResolveDialog(
            applied,
            disk,
            SETTINGS_DIALOG.persona_label_active,
            SETTINGS_DIALOG.persona_label_disk,
            SETTINGS_DIALOG.persona_source_file,
            parent,
        ).exec()
