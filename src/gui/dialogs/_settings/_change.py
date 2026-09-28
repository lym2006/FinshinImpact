# src/gui/dialogs/_settings/_change.py
"""变更确认弹窗（内部实现）

- 提供配置变更表格 diff 的二次确认
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
from ..._theme import CHANGE_DIALOG, SETTINGS_DIALOG
from .._base import BaseDialog
from ._diff import make_diff_cell, split_diff, to_lines


class ChangeConfirmDialog(BaseDialog):
    """配置变更二次确认弹窗"""

    def __init__(
        self,
        logs: list[tuple[str, ConfigValue, ConfigValue]],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent, title=CHANGE_DIALOG.title)
        self.setStyleSheet(build_change_dialog_qss())
        self.setMinimumSize(CHANGE_DIALOG.min_width, CHANGE_DIALOG.min_height)
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
        layout.setSpacing(SETTINGS_DIALOG.tab_spacing)
        tip = QLabel(CHANGE_DIALOG.tip_text)
        layout.addWidget(tip)
        layout.addWidget(self._make_table(logs))
        layout.addLayout(self._make_buttons())

    def _make_table(
        self, logs: list[tuple[str, ConfigValue, ConfigValue]]
    ) -> QTableWidget:
        """变更 diff 表格"""
        table = QTableWidget(len(logs), CHANGE_DIALOG.diff_columns)
        table.setObjectName("change_table")
        table.setHorizontalHeaderLabels(
            [CHANGE_DIALOG.col_key, CHANGE_DIALOG.col_ori, CHANGE_DIALOG.col_mod]
        )
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        # 行高按等宽字体度量：行数 × 字高 + 留白
        mono = CHANGE_DIALOG.mono_family
        line_h = QFontMetrics(QFont(mono, CHANGE_DIALOG.mono_font_size)).height()
        for row, (key, ori, mod) in enumerate(logs):
            left, right = split_diff(to_lines(ori), to_lines(mod))
            name_cell = QTableWidgetItem(str(key))
            name_cell.setToolTip(name_cell.text())
            table.setItem(row, 0, name_cell)
            table.setCellWidget(row, 1, make_diff_cell(left, mono))
            table.setCellWidget(row, 2, make_diff_cell(right, mono))
            shown = min(
                max(len(left), len(right), CHANGE_DIALOG.row_min_lines),
                CHANGE_DIALOG.row_max_lines,
            )
            table.setRowHeight(row, shown * line_h + CHANGE_DIALOG.row_pad)
        return table

    def _make_buttons(self) -> QHBoxLayout:
        """返回修改 / 确认保存"""
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_cancel = QPushButton(CHANGE_DIALOG.cancel_text)
        btn_cancel.clicked.connect(self.reject)
        btn_ok = QPushButton(CHANGE_DIALOG.confirm_text)
        btn_ok.setObjectName("btn_primary")
        btn_ok.clicked.connect(self.accept)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_ok)
        return btn_layout
