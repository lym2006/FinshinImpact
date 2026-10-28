# src/ui/_dialogs/_settings/_persona.py
"""人设正文入口

- 面板给预览、编辑与从文件重新加载三个入口，都不写文件
- 预览渲染草稿正文，只在草稿未落盘时提示一句
- 重载按钮才读实例文件，与当前正文不一致即开两栏比对再问一句用哪份
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
from utils.init_files import save_persona_pending
from utils.persona import (
    applied_persona_text,
    draft_persona_text,
    inject_owner,
    read_persona_text,
    set_draft_persona,
)

from ..._primitives import make_button
from .._base import BaseDialog
from .._notice import NoticeDialog
from ._persona_edit import PersonaDiffDialog, PersonaEditorDialog

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

    - 正文取面板草稿并按 markdown 渲染
    - 草稿没落盘才在窗底提示一句，一致时窗底干净
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
        draft = draft_persona_text()
        body.setMarkdown(inject_owner(draft, owner_id))
        layout.addWidget(body, stretch=1)

        if draft != applied_persona_text():
            tip = QLabel(SETTINGS_DIALOG.persona_pending)
            tip.setWordWrap(True)
            layout.addWidget(tip)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_close = QPushButton(SETTINGS_DIALOG.persona_close_text)
        btn_close.clicked.connect(self.accept)
        btn_close.setDefault(True)
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)


class PersonaConflictDialog(BaseDialog):
    """人设正文不一致取用确认

    - 只在面板点「从文件重新加载」时弹，运行期不自动读文件
    - 磁盘副本与当前正文一致即只提示一句，不改动任何东西
    - 先看两栏比对再决定用哪份，比对窗关掉不影响本窗
    - 两份都不当场生效，覆盖文件与换正文都等保存那一步
    - 关窗不算选，缓存与文件原样并存，要重载再点一次
    """

    def __init__(self, disk: str, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent, title=SETTINGS_DIALOG.persona_conflict_title)

        # 没选即 None，Esc 与标题栏关闭都走这条
        self.use_disk: bool | None = None

        # 比对窗要展示的磁盘快照，与本次提问读到的那份同一次读取
        self._disk = disk
        self.set_always_on_top()
        self.setStyleSheet(build_settings_dialog_qss())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(*[SETTINGS_DIALOG.input_padding_h] * _MARGIN_EDGES)
        layout.setSpacing(SETTINGS_DIALOG.desc_spacing)
        tip = QLabel(SETTINGS_DIALOG.persona_conflict_text)
        tip.setWordWrap(True)
        layout.addWidget(tip)
        layout.addLayout(self._make_buttons())

    @staticmethod
    def resolve(parent: QWidget | None = None) -> None:
        """按实例文件与当前正文的比对结果决定提示还是问一句

        - 一致即只报无变化，两份内容本就相同
        - 选完落一条取用记录，两份正文都存着，没保存就重启也拼得回比对
        - 用文件版本即把文件正文放进草稿，生效缓存与文件都不动
        - 两条都不当场生效，覆盖文件与换正文都等保存那一步
        - 关窗不算选，缓存与文件原样并存，要重载再点一次
        """
        disk = read_persona_text()[0]
        applied = applied_persona_text()
        if disk == applied:
            NoticeDialog.notify(SETTINGS_DIALOG.persona_reload_same, parent=parent)
            return
        dialog = PersonaConflictDialog(disk, parent=parent)
        dialog.exec()
        if dialog.use_disk is None:
            return
        save_persona_pending(applied, disk)
        text = SETTINGS_DIALOG.persona_reload_applied
        if dialog.use_disk:
            set_draft_persona(disk)
            text = SETTINGS_DIALOG.persona_reload_disk
        NoticeDialog.notify(
            text,
            parent=parent,
            title=SETTINGS_DIALOG.persona_choice_title,
            bold=True,
        )

    def _make_buttons(self) -> QHBoxLayout:
        """查看变化 / 用生效版本 / 用文件版本"""
        btn_layout = QHBoxLayout()
        btn_view = make_button(SETTINGS_DIALOG.persona_view_diff, ButtonStyle.PERSONA)
        btn_view.clicked.connect(self._on_view_diff)
        btn_layout.addWidget(btn_view)
        btn_layout.addStretch()
        btn_applied = QPushButton(SETTINGS_DIALOG.persona_conflict_applied)
        btn_applied.clicked.connect(lambda: self._choose(False))
        btn_disk = make_button(
            SETTINGS_DIALOG.persona_conflict_disk, ButtonStyle.PRIMARY
        )
        btn_disk.clicked.connect(lambda: self._choose(True))
        btn_disk.setDefault(True)
        btn_layout.addWidget(btn_applied)
        btn_layout.addWidget(btn_disk)
        return btn_layout

    def _on_view_diff(self) -> None:
        """两栏比对生效正文与磁盘文件正文

        - 左取生效版本，右取文件版本，与两颗按钮的取舍同序
        """
        PersonaDiffDialog.show_diff(applied_persona_text(), self._disk, parent=self)

    def _choose(self, use_disk: bool) -> None:
        """记下取舍再收窗"""
        self.use_disk = use_disk
        self.accept()


class PersonaPreviewRow(QWidget):
    """人设正文入口行

    - 标签占位与字段行同宽，按钮才与其他输入框左对齐
    - 预览与编辑各开一窗，都不写文件
    - 重载按钮是全窗唯一读实例文件的地方
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
        """弹窗渲染草稿正文"""
        if self._owner is None:
            return
        owner_id = _text_of(self._owner).strip()
        _PersonaPreviewDialog(owner_id, parent=self.window()).exec()

    def _on_edit_clicked(self) -> None:
        """编辑草稿正文

        - 确认只更新草稿，落盘归配置面板保存那一步
        """
        edited = PersonaEditorDialog.edit(draft_persona_text(), parent=self.window())
        if edited is None:
            return
        set_draft_persona(edited)
        NoticeDialog.notify(SETTINGS_DIALOG.persona_pending, parent=self.window())

    def _on_reload_clicked(self) -> None:
        """比对实例文件与当前正文，按所选起记录或进草稿

        - 读文件与比对都收在这一颗按钮，一致只提示一句
        - 选完不当场生效，覆盖文件与换正文都等保存那一步
        """
        PersonaConflictDialog.resolve(parent=self.window())
