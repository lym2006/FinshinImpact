# src/gui/dialogs/_settings/_persona.py
"""人设预览

- 组装配置页当前填写的人设正文，点按钮弹窗只读展示
- 提供打开实例人设文件入口
"""

import os
from typing import TypeAlias

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from utils.init_files import PERSONALITY_FILE
from utils.persona import PersonaSource, build_persona, persona_source

from ..._qss import build_settings_dialog_qss
from ..._theme import SETTINGS_DIALOG
from .._base import BaseDialog
from .._notice import NoticeDialog

# 人设字符串被用户改成单行时渲染控件会回落 QLineEdit
_TextWidget: TypeAlias = QTextEdit | QLineEdit

# 来源标识到弹窗提示语的映射
_SOURCE_HINTS = {
    PersonaSource.FILE: SETTINGS_DIALOG.persona_from_file,
    PersonaSource.CONFIG: SETTINGS_DIALOG.persona_from_config,
    PersonaSource.MISSING: SETTINGS_DIALOG.persona_missing,
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

    - 打开即渲染最终正文，底部标注正文来源
    """

    def __init__(self, text: str, hint: str, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent, title=SETTINGS_DIALOG.persona_title)
        self.set_always_on_top()
        self.setStyleSheet(build_settings_dialog_qss())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(*[SETTINGS_DIALOG.input_padding_h] * _MARGIN_EDGES)
        layout.setSpacing(SETTINGS_DIALOG.desc_spacing)

        body = QTextEdit()
        body.setObjectName("persona_preview")
        body.setReadOnly(True)
        body.setPlainText(text)

        # 最小尺寸即默认尺寸，窗口拉大时正文框随布局弹性填满
        body.setMinimumSize(
            SETTINGS_DIALOG.persona_preview_width,
            SETTINGS_DIALOG.persona_preview_height,
        )
        layout.addWidget(body, stretch=1)

        tip = QLabel(hint)
        tip.setWordWrap(True)
        layout.addWidget(tip)

        btn = QPushButton(SETTINGS_DIALOG.persona_close_text)
        btn.setObjectName("btn_primary")
        btn.clicked.connect(self.accept)
        btn.setDefault(True)
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)


class PersonaPreviewRow(QWidget):
    """人设预览按钮行

    - 与人设输入行共槽等高互斥，切换勾选态整页不跳动
    - 预览弹窗实时取当前编辑值，文件缺失回退也在弹窗标注
    """

    def __init__(self, label_width: int = 0, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._use_file: QCheckBox | None = None
        self._personality: _TextWidget | None = None
        self._owner: _TextWidget | None = None
        self._slot: QStackedWidget | None = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(*[SETTINGS_DIALOG.margin] * _MARGIN_EDGES)
        layout.setSpacing(SETTINGS_DIALOG.desc_spacing)

        # 占位标签撑出与字段行同宽的左列，按钮才与其他输入框左对齐
        spacer = QLabel()
        spacer.setMinimumWidth(label_width)

        btn_preview = QPushButton(SETTINGS_DIALOG.persona_preview_text)
        btn_preview.setObjectName("btn_persona_preview")
        btn_preview.clicked.connect(self._on_preview_clicked)

        btn_open = QPushButton(SETTINGS_DIALOG.persona_open_text)
        btn_open.setObjectName("btn_persona_open")
        btn_open.clicked.connect(self._on_open_clicked)

        # 槽位按输入行取高，本行内容顶部对齐不悬空
        layout.addWidget(spacer)
        layout.addWidget(btn_preview, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addWidget(btn_open, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addStretch()

    def bind(
        self,
        use_file: QWidget,
        personality: QWidget,
        owner: QWidget,
        slot: QStackedWidget,
    ) -> bool:
        """绑定联动源

        - 任一控件类型不符返回 False，由调用方放弃堆叠改回原布局
        - slot 为输入行与本行共用的堆叠槽位，页面装配由调用方完成
        """
        if not isinstance(use_file, QCheckBox):
            return False
        if not isinstance(personality, _TextWidget) or not isinstance(
            owner, _TextWidget
        ):
            return False

        self._use_file, self._personality, self._owner = use_file, personality, owner
        self._slot = slot
        use_file.toggled.connect(lambda _checked: self.sync())
        return True

    def sync(self) -> None:
        """按勾选态切堆叠槽页

        - 堆叠高度恒取两页最大值，切换不跳版面
        """
        use_file = bool(self._use_file and self._use_file.isChecked())
        if self._slot is not None:
            self._slot.setCurrentIndex(1 if use_file else 0)

    def _on_preview_clicked(self) -> None:
        """弹窗展示最终正文与来源"""
        if self._personality is None or self._owner is None:
            return
        use_file = bool(self._use_file and self._use_file.isChecked())
        text = build_persona(
            _text_of(self._personality),
            use_file,
            _text_of(self._owner).strip(),
        )
        hint = _SOURCE_HINTS[persona_source(use_file)]
        _PersonaPreviewDialog(text, hint, parent=self.window()).exec()

    def _on_open_clicked(self) -> None:
        """打开实例人设文件

        - 文件缺失或系统拒绝一律弹窗告知，不静默失败
        """
        if not PERSONALITY_FILE.is_file():
            self._notify(f"{PERSONALITY_FILE}\n{SETTINGS_DIALOG.persona_file_miss}")
            return
        try:
            os.startfile(PERSONALITY_FILE)
        except OSError as e:
            self._notify(str(e))

    def _notify(self, detail: str) -> None:
        """弹出打开失败提示"""
        NoticeDialog.notify(f"{SETTINGS_DIALOG.persona_open_fail}\n{detail}", self)
