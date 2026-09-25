# src/gui/dialogs/_settings/_change.py
"""变更确认弹窗（内部实现）

- 提供配置变更表格 diff 的二次确认
- 承载未修改提示的家族化入口
"""

from PySide6.QtGui import QFont, QFontMetrics
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from utils.config.models import ConfigValue

from ..._qss import build_change_dialog_qss
from ..._theme import CHANGE_DIALOG as CHANGE
from ..._theme import HINT_DIALOG as HINT
from ..._theme import SETTINGS_DIALOG as DIALOG
from .._base import BaseDialog
from .._hint import HintDialog
from ._diff import make_diff_cell, split_diff, to_lines


class NotChangedDialog:
    """配置未修改提示弹窗"""

    @staticmethod
    def show(parent=None, text: str = HINT.not_changed) -> None:
        """家族化模态展示"""
        HintDialog.notify(text, parent=parent)


class ChangeConfirmDialog(BaseDialog):
    """配置变更二次确认弹窗"""

    def __init__(
        self,
        logs: list[tuple[str, ConfigValue, ConfigValue]],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent, title=CHANGE.title)
        self.setStyleSheet(build_change_dialog_qss())
        self.setMinimumSize(CHANGE.min_width, CHANGE.min_height)
        self._build_ui(logs)

    @staticmethod
    def confirm(
        logs: list[tuple[str, ConfigValue, ConfigValue]],
        parent: QWidget | None = None,
    ) -> bool:
        """模态展示

        返回是否确认保存。
        """
        dialog = ChangeConfirmDialog(logs, parent=parent)
        return dialog.exec() == dialog.DialogCode.Accepted

    def _build_ui(self, logs: list[tuple[str, ConfigValue, ConfigValue]]) -> None:
        """提示语 + diff 表格 + 按钮区"""
        layout = QVBoxLayout(self)
        layout.setSpacing(DIALOG.tab_spacing)
        tip = QLabel(CHANGE.tip_text)
        layout.addWidget(tip)
        layout.addWidget(self._make_table(logs))
        layout.addLayout(self._make_buttons())

    def _make_table(
        self, logs: list[tuple[str, ConfigValue, ConfigValue]]
    ) -> QTableWidget:
        """变更 diff 表格"""
        table = QTableWidget(len(logs), CHANGE.diff_columns)
        table.setObjectName("change_table")
        table.setHorizontalHeaderLabels(
            [CHANGE.col_key, CHANGE.col_ori, CHANGE.col_mod]
        )
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        # 行高按等宽字体度量：行数 × 字高 + 留白
        mono = CHANGE.mono_family
        line_h = QFontMetrics(QFont(mono, CHANGE.mono_font_size)).height()
        for row, (key, ori, mod) in enumerate(logs):
            left, right = split_diff(to_lines(ori), to_lines(mod))
            name_cell = QTableWidgetItem(str(key))
            name_cell.setToolTip(name_cell.text())
            table.setItem(row, 0, name_cell)
            table.setCellWidget(row, 1, make_diff_cell(left, mono))
            table.setCellWidget(row, 2, make_diff_cell(right, mono))
            shown = min(
                max(len(left), len(right), CHANGE.row_min_lines),
                CHANGE.row_max_lines,
            )
            table.setRowHeight(row, shown * line_h + CHANGE.row_pad)
        return table

    def _make_buttons(self) -> QHBoxLayout:
        """返回修改 / 确认保存"""
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_cancel = QPushButton(CHANGE.cancel_text)
        btn_cancel.clicked.connect(self.reject)
        btn_ok = QPushButton(CHANGE.confirm_text)
        btn_ok.setObjectName("btn_primary")
        btn_ok.clicked.connect(self.accept)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_ok)
        return btn_layout
