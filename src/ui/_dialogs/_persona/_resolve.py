# src/ui/_dialogs/_persona/_resolve.py
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
    QScrollBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from skin.qss import build_change_dialog_qss
from skin.theme import CHANGE_DIALOG, SETTINGS_DIALOG, ButtonStyle

from ..._bridge import gui_bridge
from ..._primitives import make_button
from .._base import BaseDialog
from .._diff import diff_html, make_diff_cell, split_diff_aligned, to_lines
from .._notice import NoticeDialog

# Qt 布局四边
_MARGIN_EDGES = 4  # setContentsMargins 收上下左右四个值


class PersonaResolveDialog(BaseDialog):
    """人设正文拍板窗

    - 两栏比对旧新两份正文，栏名由调用方给
    - 未改动段折起，两栏滚动作同进退
    - 选中一份进二次确认，确认才发落盘信号
    - 标题栏关闭与 Esc 一律拦下，拍了板才许走
    """

    def __init__(
        self,
        old: str,
        new: str,
        old_label: str,
        new_label: str,
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

        # 选定那份的正文与栏名，栏名兼作落盘提示里的来源词
        self._old = old
        self._new = new
        self._old_label = old_label
        self._new_label = new_label
        self._chosen: tuple[str, str] = ("", "")
        self._folded = True  # 未改动段是否折起
        self._has_skip = False  # 真折起过才给展开开关
        self._syncing = False  # 两栏互抄滚动值的回环门

        layout = QVBoxLayout(self)
        layout.setContentsMargins(*[SETTINGS_DIALOG.input_padding_h] * _MARGIN_EDGES)
        layout.setSpacing(SETTINGS_DIALOG.tab_spacing)
        layout.addLayout(self._make_tip_row())
        layout.addLayout(self._make_columns(old_label, new_label), 1)
        self._confirm_row = self._make_confirm_row()
        layout.addWidget(self._confirm_row)
        self._repaint()
        self._link_scroll()

    @staticmethod
    def resolve(
        old: str,
        new: str,
        old_label: str,
        new_label: str,
        parent: QWidget | None = None,
    ) -> None:
        """两份一致即只提示一句，不一致才开窗拍板

        - 拍完的正文由窗自己发信号，调用方不取回值
        """
        if old == new:
            NoticeDialog.notify(SETTINGS_DIALOG.persona_resolve_same, parent=parent)
            return
        PersonaResolveDialog(old, new, old_label, new_label, parent).exec()

    def _make_tip_row(self) -> QHBoxLayout:
        """提示语与折叠开关同排"""
        row = QHBoxLayout()
        row.addWidget(QLabel(SETTINGS_DIALOG.persona_resolve_text))
        row.addStretch()
        self._btn_fold = QPushButton(SETTINGS_DIALOG.persona_resolve_expand)
        self._btn_fold.clicked.connect(self._toggle_fold)
        row.addWidget(self._btn_fold)
        return row

    def _make_columns(self, old_label: str, new_label: str) -> QHBoxLayout:
        """左旧右新两栏 diff，栏底各一颗「用这份」

        - 右栏是改动的那份，吃主按钮档并拿默认焦点
        - 左栏走次要档，与右栏并列但不抢默认档
        - 正文由 _repaint 填，折叠与展开两态共用一条路径
        """
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
        left, self._left_cell = self._make_column(old_label, self._btn_old)
        right, self._right_cell = self._make_column(new_label, self._btn_new)
        columns.addWidget(left, stretch=1)
        columns.addWidget(right, stretch=1)
        return columns

    def _make_column(
        self, label: str, button: QPushButton
    ) -> tuple[QWidget, QTextEdit]:
        """建一栏 diff 单元格与栏底按钮"""
        column = QWidget(self)
        layout = QVBoxLayout(column)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SETTINGS_DIALOG.desc_spacing)
        layout.addWidget(QLabel(label))
        cell = make_diff_cell([], CHANGE_DIALOG.mono_family)
        layout.addWidget(cell, stretch=1)
        layout.addWidget(button)
        return column, cell

    def _repaint(self) -> None:
        """按折叠态重画两栏，开关的字面与在场一起换"""
        context = SETTINGS_DIALOG.persona_resolve_context if self._folded else None
        left, right = split_diff_aligned(
            to_lines(self._old),
            to_lines(self._new),
            SETTINGS_DIALOG.persona_resolve_skip,
            context,
        )
        if self._folded:
            self._has_skip = any(kind == "skip" for line in left for kind, _ in line)
        mono = CHANGE_DIALOG.mono_family
        for cell, lines in ((self._left_cell, left), (self._right_cell, right)):
            cell.setHtml(diff_html(lines, mono))
        self._btn_fold.setVisible(self._has_skip)
        self._btn_fold.setText(
            SETTINGS_DIALOG.persona_resolve_expand
            if self._folded
            else SETTINGS_DIALOG.persona_resolve_collapse
        )

    def _toggle_fold(self) -> None:
        """整份铺开与折起两态来回切"""
        self._folded = not self._folded
        self._repaint()

    def _link_scroll(self) -> None:
        """两栏纵向滚动手拉手

        - 补位之后两栏行数相同，值相等即同一行落在同一高度
        """
        bars = (
            self._left_cell.verticalScrollBar(),
            self._right_cell.verticalScrollBar(),
        )
        for source, target in ((bars[0], bars[1]), (bars[1], bars[0])):
            source.valueChanged.connect(
                lambda value, to=target: self._follow_scroll(value, to)
            )

    def _follow_scroll(self, value: int, target: QScrollBar) -> None:
        """一栏滚了即把值抄给另一栏，抄的过程不回手"""
        if self._syncing:
            return
        self._syncing = True
        target.setValue(value)
        self._syncing = False

    def _make_confirm_row(self) -> QWidget:
        """二次确认行，拍板前收起

        - 只给「再看看」与「确认」两颗钮
        """
        row = QWidget(self)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SETTINGS_DIALOG.desc_spacing)
        self._confirm_tip = QLabel("")
        layout.addWidget(self._confirm_tip)
        layout.addStretch()
        btn_back = QPushButton(SETTINGS_DIALOG.persona_resolve_back)
        btn_back.clicked.connect(self._restore_choose)
        self._btn_commit = make_button(
            SETTINGS_DIALOG.confirm_text, ButtonStyle.PRIMARY
        )
        self._btn_commit.clicked.connect(self._on_commit)
        layout.addWidget(btn_back)
        layout.addWidget(self._btn_commit)
        row.setVisible(False)
        return row

    def _on_use(self, button: QPushButton) -> None:
        """记下选中的那份正文与其栏名，进二次确认"""
        is_new = button is self._btn_new
        self._chosen = (
            (self._new, self._new_label) if is_new else (self._old, self._old_label)
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
        - 折叠开关属比对段，二次确认时收起
        """
        self._confirm_row.setVisible(confirm)
        self._btn_old.setVisible(not confirm)
        self._btn_new.setVisible(not confirm)
        self._btn_fold.setVisible(self._has_skip and not confirm)
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
