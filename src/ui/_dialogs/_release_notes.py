# src/ui/_dialogs/_release_notes.py
"""版本变化弹窗

- 左列版本清单，右侧正文按选中版本渲染，超出高度由滚动条接住
"""

from collections.abc import Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QTextBrowser, QVBoxLayout, QWidget

from skin.qss import build_release_notes_dialog_qss
from skin.theme import RELEASE_NOTES_DIALOG, ButtonStyle, ObjectName
from utils.check import ReleaseNote

from .._primitives import ThemedList, make_button
from ._base import BaseDialog

# Qt 布局四边
_MARGIN_EDGES = 4  # setContentsMargins 收上下左右四个值

# 无选中行时的行号
_NO_ROW = -1


def _row_text(note: ReleaseNote) -> str:
    """清单一行的版本标签文案"""
    if note.prerelease:
        return RELEASE_NOTES_DIALOG.prerelease_text.format(tag=note.tag)
    return note.tag


class ReleaseNotesDialog(BaseDialog):
    """版本变化弹窗"""

    def __init__(
        self,
        notes: Sequence[ReleaseNote],
        focus_tag: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent, title=RELEASE_NOTES_DIALOG.title)
        self.set_always_on_top()
        self.setStyleSheet(build_release_notes_dialog_qss())
        self._bodies = tuple(note.body for note in notes)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(*[RELEASE_NOTES_DIALOG.pad] * _MARGIN_EDGES)
        layout.setSpacing(RELEASE_NOTES_DIALOG.spacing)

        # QTextEdit 没有链接信号，只读视图要用 QTextBrowser
        self._view = QTextBrowser(parent=self)
        self._view.setObjectName(ObjectName.RELEASE_NOTES_VIEW)

        # 默认只在 Qt 内部找锚点，点开即报找不到，交系统浏览器接手
        self._view.setOpenExternalLinks(True)

        panes = QHBoxLayout()
        panes.addWidget(self._build_list(notes, focus_tag))
        panes.addWidget(self._view, 1)
        layout.addLayout(panes)
        btn = make_button(RELEASE_NOTES_DIALOG.ok_text, ButtonStyle.PRIMARY)
        btn.clicked.connect(self.accept)
        btn.setDefault(True)
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)

        # 尺寸定死：正文再长也不把窗口顶出屏幕，读不完的部分交给滚动
        self.setFixedSize(RELEASE_NOTES_DIALOG.width, RELEASE_NOTES_DIALOG.height)

    def _build_list(self, notes: Sequence[ReleaseNote], focus_tag: str) -> ThemedList:
        """按版本建左侧清单，选中行决定右侧正文"""
        listing = ThemedList(parent=self)
        listing.setObjectName(ObjectName.LIST_WIDGET)
        listing.setFixedWidth(RELEASE_NOTES_DIALOG.list_width)
        for note in notes:
            listing.addItem(_row_text(note))
        listing.currentRowChanged.connect(self._show_body)

        # 未命中焦点版本即落回最新一版，空清单留无选中
        row = _NO_ROW
        if notes:
            row = next((i for i, note in enumerate(notes) if note.tag == focus_tag), 0)
        listing.setCurrentRow(row)
        return listing

    def _show_body(self, row: int) -> None:
        """按选中行换正文"""
        self._view.setMarkdown(self._bodies[row] if row >= 0 else "")

    @staticmethod
    def show_release_notes(
        notes: Sequence[ReleaseNote],
        focus_tag: str = "",
        parent: QWidget | None = None,
    ) -> None:
        """模态展示各版本发布说明"""
        ReleaseNotesDialog(notes, focus_tag, parent=parent).exec()
