# src/ui/_dialogs/_settings/_persona_edit.py
"""人设正文编辑与变更大窗

- 编辑窗交出待生效正文，确认只更新缓存不落盘
- 大窗两栏比对，只读展示或要一句确认才覆盖
- 清理历史归配置面板保存，两窗都只动内存
"""

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from skin.qss import build_change_dialog_qss, build_settings_dialog_qss
from skin.theme import CHANGE_DIALOG, SETTINGS_DIALOG, ButtonStyle, ObjectName
from utils.persona import read_template_text

from ..._primitives import make_button
from .._base import BaseDialog
from .._notice import NoticeDialog
from ._diff import make_diff_cell, split_diff, to_lines

_MARGIN_EDGES = 4  # setContentsMargins 收上下左右四个值


class PersonaEditorDialog(BaseDialog):
    """人设正文编辑器

    - 正文按原文展示，主人 id 留占位符
    - 确认交出内容，用模板覆盖先比对再换编辑框里的字
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
        """编辑框换成内置模板正文

        - 读不出模板与内容一致都只提示，一个字不改
        - 有差异先开两栏比对，确认覆盖才换编辑框里的字
        """
        template = read_template_text()
        if not template:
            NoticeDialog.notify(SETTINGS_DIALOG.persona_no_template, parent=self)
            return
        current = self._body.toPlainText()
        if template == current:
            NoticeDialog.notify(SETTINGS_DIALOG.persona_template_same, parent=self)
            return
        if PersonaDiffDialog.confirm_overwrite(current, template, parent=self):
            self._body.setPlainText(template)


class PersonaDiffDialog(BaseDialog):
    """人设正文变更大窗

    - 两栏按原文比对，主人 id 留占位符不注入
    - 交出确认文案即变成覆盖前的确认窗，取消不改编辑框
    """

    def __init__(
        self,
        old: str,
        new: str,
        parent: QWidget | None = None,
        confirm_text: str | None = None,
    ) -> None:
        super().__init__(
            parent=parent,
            title=(
                SETTINGS_DIALOG.persona_template_title
                if confirm_text
                else SETTINGS_DIALOG.persona_diff_title
            ),
        )
        self.set_always_on_top()
        self.setStyleSheet(build_change_dialog_qss())
        self.setMinimumSize(
            SETTINGS_DIALOG.persona_diff_width,
            SETTINGS_DIALOG.persona_diff_height,
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(*[SETTINGS_DIALOG.input_padding_h] * _MARGIN_EDGES)
        layout.setSpacing(SETTINGS_DIALOG.tab_spacing)
        layout.addLayout(self._make_columns(old, new), stretch=1)
        layout.addLayout(self._make_buttons(confirm_text))

    @staticmethod
    def show_diff(old: str, new: str, parent: QWidget | None = None) -> None:
        """模态展示两栏比对"""
        PersonaDiffDialog(old, new, parent=parent).exec()

    @staticmethod
    def confirm_overwrite(
        current: str, template: str, parent: QWidget | None = None
    ) -> bool:
        """模态比对现值与模板，交是否确认覆盖

        - 关闭与取消同样算不覆盖
        """
        dialog = PersonaDiffDialog(
            current,
            template,
            parent=parent,
            confirm_text=SETTINGS_DIALOG.persona_template_ok,
        )
        return dialog.exec() == dialog.DialogCode.Accepted

    def _make_buttons(self, confirm_text: str | None) -> QHBoxLayout:
        """关闭，或取消加确认覆盖

        - 确认覆盖按危险档，与编辑窗那颗同色
        """
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        if confirm_text is None:
            btn_last = QPushButton(SETTINGS_DIALOG.persona_close_text)
            btn_last.clicked.connect(self.accept)
        else:
            btn_cancel = QPushButton(SETTINGS_DIALOG.cancel_text)
            btn_cancel.clicked.connect(self.reject)
            btn_layout.addWidget(btn_cancel)
            btn_last = make_button(confirm_text, ButtonStyle.DANGER)
            btn_last.clicked.connect(self.accept)
        btn_last.setDefault(True)
        btn_layout.addWidget(btn_last)
        return btn_layout

    def _make_columns(self, old: str, new: str) -> QHBoxLayout:
        """左当前正文、右变更后的两栏 diff"""
        mono = CHANGE_DIALOG.mono_family
        left, right = split_diff(to_lines(old), to_lines(new))
        columns = QHBoxLayout()
        columns.setSpacing(SETTINGS_DIALOG.tab_spacing)
        for title, lines in zip(
            (
                SETTINGS_DIALOG.persona_diff_col_ori,
                SETTINGS_DIALOG.persona_diff_col_mod,
            ),
            (left, right),
            strict=True,
        ):
            column = QVBoxLayout()
            column.setSpacing(SETTINGS_DIALOG.desc_spacing)
            column.addWidget(QLabel(title))
            column.addWidget(make_diff_cell(lines, mono), stretch=1)
            columns.addLayout(column, stretch=1)
        return columns
