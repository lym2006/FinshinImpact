# src/ui/_dialogs/_settings/_persona.py
"""人设预览

- 弹窗展示磁盘人设副本的当前正文并注入主人 id，附来源与对账状态
- 提供打开实例人设文件入口与用默认模板覆盖副本的入口
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
from skin.theme import NOTICE_DIALOG, SETTINGS_DIALOG, ButtonStyle, ObjectName
from system.shell import open_path
from utils.init_files import (
    PersonaState,
    apply_persona_template,
    check_persona_state,
    ensure_persona_copy,
)
from utils.paths import PERSONALITY_FILE
from utils.persona import (
    PersonaSource,
    applied_persona_text,
    inject_owner,
    read_persona_text,
)

from ..._primitives import make_button
from .._base import BaseDialog
from .._notice import NoticeDialog

# 人设字符串被用户改成单行时渲染控件会回落 QLineEdit
_TextWidget: TypeAlias = QTextEdit | QLineEdit

# 正文来源到弹窗提示语的映射
_SOURCE_HINTS = {
    PersonaSource.FILE: SETTINGS_DIALOG.persona_from_file,
    PersonaSource.TEMPLATE: SETTINGS_DIALOG.persona_from_template,
    PersonaSource.EMPTY: SETTINGS_DIALOG.persona_missing,
}

# 副本与默认模板关系到弹窗提示语的映射
_STATE_HINTS = {
    PersonaState.SAME: SETTINGS_DIALOG.persona_same,
    PersonaState.OUTDATED: SETTINGS_DIALOG.persona_outdated,
    PersonaState.EDITED: SETTINGS_DIALOG.persona_edited,
    PersonaState.UNREADABLE: SETTINGS_DIALOG.persona_unreadable,
}

# Qt 布局四边
_MARGIN_EDGES = 4  # setContentsMargins 收上下左右四个值


def _text_of(widget: _TextWidget) -> str:
    """取文本控件当前值"""
    if isinstance(widget, QTextEdit):
        return widget.toPlainText()
    return widget.text()


class _PersonaPreviewDialog(BaseDialog):
    """人设正文弹窗

    - 打开即渲染磁盘当前正文，底部标注来源、对账状态与是否已生效
    - 覆盖副本当场重写文件并刷新窗内提示，正文即所见
    """

    def __init__(self, owner_id: str, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent, title=SETTINGS_DIALOG.persona_title)
        self._owner_id = owner_id
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
        self._body = body
        layout.addWidget(body, stretch=1)

        tip = QLabel()
        tip.setWordWrap(True)
        self._tip = tip
        layout.addWidget(tip)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_apply = make_button(SETTINGS_DIALOG.persona_apply_text, ButtonStyle.PRIMARY)
        btn_apply.clicked.connect(self._on_apply_clicked)
        btn_close = QPushButton(SETTINGS_DIALOG.persona_close_text)
        btn_close.clicked.connect(self.accept)
        btn_close.setDefault(True)
        btn_layout.addWidget(btn_apply)
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)

        self.refresh()

    def refresh(self) -> None:
        """按磁盘当前状态重画正文与三行提示"""
        text, source = read_persona_text()
        self._body.setPlainText(inject_owner(text, self._owner_id))
        self._tip.setText("\n".join(self._hints(text, source)))

    def _hints(self, text: str, source: PersonaSource) -> tuple[str, ...]:
        """取来源、对账与生效三行提示语"""
        applied = (
            SETTINGS_DIALOG.persona_applied
            if text == applied_persona_text()
            else SETTINGS_DIALOG.persona_pending
        )
        return _SOURCE_HINTS[source], _STATE_HINTS[check_persona_state()], applied

    def _on_apply_clicked(self) -> None:
        """用默认模板覆盖实例副本"""
        if not apply_persona_template():
            NoticeDialog.notify(NOTICE_DIALOG.persona_apply_fail, parent=self)
            return
        self.refresh()


class PersonaPreviewRow(QWidget):
    """人设正文入口行

    - 标签占位与字段行同宽，按钮才与其他输入框左对齐
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
            SETTINGS_DIALOG.persona_preview_text, ButtonStyle.PERSONA_PREVIEW
        )
        btn_preview.clicked.connect(self._on_preview_clicked)

        btn_open = make_button(
            SETTINGS_DIALOG.persona_open_text, ButtonStyle.PERSONA_OPEN
        )
        btn_open.clicked.connect(self._on_open_clicked)

        # 本行内容顶部对齐，不与上方多行输入框的底边缠斗
        layout.addWidget(title)
        layout.addWidget(btn_preview, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addWidget(btn_open, alignment=Qt.AlignmentFlag.AlignTop)
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
        """弹窗展示磁盘正文"""
        if self._owner is None:
            return
        owner_id = _text_of(self._owner).strip()
        _PersonaPreviewDialog(owner_id, parent=self.window()).exec()

    def _on_open_clicked(self) -> None:
        """打开实例人设文件

        - 副本没建先从默认模板建好，建不出才弹窗告知
        """
        if not ensure_persona_copy():
            self._notify(
                f"{PERSONALITY_FILE}\n{SETTINGS_DIALOG.persona_file_create_fail}"
            )
            return
        try:
            open_path(PERSONALITY_FILE)
        except OSError as e:
            self._notify(str(e))

    def _notify(self, detail: str) -> None:
        """弹出打开失败提示"""
        NoticeDialog.notify(f"{SETTINGS_DIALOG.persona_open_fail}\n{detail}", self)
