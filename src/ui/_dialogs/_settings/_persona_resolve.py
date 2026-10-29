# src/ui/_dialogs/_settings/_persona_resolve.py
"""人设正文拍板窗

- 左右两栏比对两份正文，两份一致即只提示一句
- 未拍板不许关窗，拍完进二次确认才交出选定正文
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QKeyEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from skin.qss import build_change_dialog_qss
from skin.theme import CHANGE_DIALOG, SETTINGS_DIALOG, ButtonStyle

from ..._bridge import gui_bridge
from ..._primitives import make_button
from .._base import BaseDialog
from .._notice import NoticeDialog
from ._diff import make_diff_cell, split_diff, to_lines

# Qt 布局四边
_MARGIN_EDGES = 4  # setContentsMargins 收上下左右四个值


class PersonaResolveDialog(BaseDialog):
    """人设正文拍板窗

    - 两栏比对旧新两份正文，栏名由调用方给
    - 选中一份进二次确认，确认才发落盘信号
    - 标题栏关闭与 Esc 一律拦下，拍了板才许走
    """

    def __init__(
        self,
        old: str,
        new: str,
        old_label: str,
        new_label: str,
        source: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent, title=SETTINGS_DIALOG.persona_resolve_title)
        self.set_always_on_top()
        self.setStyleSheet(build_change_dialog_qss())
        self.setMinimumSize(
            SETTINGS_DIALOG.persona_resolve_width,
            SETTINGS_DIALOG.persona_resolve_height,
        )
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint)

        # 选中那一份的正文、来源词与二次确认里点的栏名
        self._old = old
        self._new = new
        self._old_label = old_label
        self._new_label = new_label
        self._old_source = f"{old_label}那一份"
        self._new_source = source
        self._chosen: tuple[str, str] = ("", "")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(*[SETTINGS_DIALOG.input_padding_h] * _MARGIN_EDGES)
        layout.setSpacing(SETTINGS_DIALOG.tab_spacing)
        tip = QLabel(SETTINGS_DIALOG.persona_resolve_text)
        tip.setWordWrap(True)
        layout.addWidget(tip)
        layout.addLayout(self._make_columns(old, new, old_label, new_label), 1)
        self._confirm_row = self._make_confirm_row()
        layout.addWidget(self._confirm_row)

    @staticmethod
    def resolve(
        old: str,
        new: str,
        old_label: str,
        new_label: str,
        source: str,
        parent: QWidget | None = None,
    ) -> None:
        """两份一致即只提示一句，不一致才开窗拍板

        - 拍完的正文由窗自己发信号，调用方不取回值
        """
        if old == new:
            NoticeDialog.notify(SETTINGS_DIALOG.persona_resolve_same, parent=parent)
            return
        PersonaResolveDialog(old, new, old_label, new_label, source, parent).exec()

    def _make_columns(
        self, old: str, new: str, old_label: str, new_label: str
    ) -> QHBoxLayout:
        """左旧右新两栏 diff，栏底各一颗「用这份」

        - 右栏是改动的那份，吃主按钮档并拿默认焦点
        - 左栏走次要档，与右栏并列但不抢默认档
        """
        mono = CHANGE_DIALOG.mono_family
        left, right = split_diff(to_lines(old), to_lines(new))
        columns = QHBoxLayout()
        columns.setSpacing(SETTINGS_DIALOG.tab_spacing)
        self._btn_old = make_button(
            SETTINGS_DIALOG.persona_resolve_use, ButtonStyle.SECONDARY
        )
        self._btn_old.clicked.connect(lambda: self._on_use(self._btn_old))
        self._btn_new = make_button(
            SETTINGS_DIALOG.persona_resolve_use, ButtonStyle.PRIMARY
        )
        self._btn_new.clicked.connect(lambda: self._on_use(self._btn_new))
        self._btn_new.setDefault(True)
        for label, lines, button in (
            (old_label, left, self._btn_old),
            (new_label, right, self._btn_new),
        ):
            columns.addWidget(self._make_column(label, lines, mono, button), stretch=1)
        return columns

    def _make_column(
        self,
        label: str,
        lines: list[list[tuple[str, str]]],
        mono: str,
        button: QPushButton,
    ) -> QWidget:
        """建一栏 diff 单元格与栏底按钮"""
        column = QWidget(self)
        layout = QVBoxLayout(column)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SETTINGS_DIALOG.desc_spacing)
        layout.addWidget(QLabel(label))
        layout.addWidget(make_diff_cell(lines, mono), stretch=1)
        layout.addWidget(button)
        return column

    def _make_confirm_row(self) -> QWidget:
        """二次确认行，拍板前收起

        - 只给「再看看」与「确认」两颗钮
        """
        row = QWidget(self)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SETTINGS_DIALOG.desc_spacing)
        self._confirm_tip = QLabel("")
        self._confirm_tip.setWordWrap(True)
        layout.addWidget(self._confirm_tip)
        layout.addStretch()
        btn_back = QPushButton(SETTINGS_DIALOG.persona_resolve_back)
        btn_back.clicked.connect(self._restore_choose)
        self._btn_commit = make_button(
            SETTINGS_DIALOG.persona_resolve_confirm, ButtonStyle.PRIMARY
        )
        self._btn_commit.clicked.connect(self._on_commit)
        layout.addWidget(btn_back)
        layout.addWidget(self._btn_commit)
        row.setVisible(False)
        return row

    def _on_use(self, button: QPushButton) -> None:
        """记下选中的那份并进二次确认"""
        is_new = button is self._btn_new
        self._chosen = (
            (self._new, self._new_source) if is_new else (self._old, self._old_source)
        )
        label = self._new_label if is_new else self._old_label
        self._confirm_tip.setText(
            SETTINGS_DIALOG.persona_resolve_confirm_text.format(label=label)
        )
        self._toggle_stage(confirm=True)

    def _restore_choose(self) -> None:
        """退回两栏比对重新选"""
        self._toggle_stage(confirm=False)

    def _toggle_stage(self, confirm: bool) -> None:
        """切换比对与确认两段

        - 两栏的「用这份」与确认行不会同时在场
        """
        self._confirm_row.setVisible(confirm)
        self._btn_old.setVisible(not confirm)
        self._btn_new.setVisible(not confirm)
        default = self._btn_commit if confirm else self._btn_new
        default.setDefault(True)
        default.setFocus()

    def _on_commit(self) -> None:
        """确认即发落盘信号并收窗"""
        gui_bridge.persona_committed.emit(*self._chosen)
        self.accept()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        """拦下标题栏关闭，拍板前不许走"""
        event.ignore()

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        """拦下 Esc，只留两颗钮里的出路"""
        if event.key() == Qt.Key.Key_Escape:
            event.accept()
            return
        super().keyPressEvent(event)
