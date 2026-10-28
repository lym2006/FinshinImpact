# src/ui/_dialogs/_settings/_change.py
"""变更确认弹窗

- 提供配置变更表格 diff 的二次确认
- 人设行排在表格外，点开才出两栏大窗
- 只改人设不出表格，没改人设不出人设行
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

from skin.qss import build_change_dialog_qss
from skin.theme import CHANGE_DIALOG, SETTINGS_DIALOG, ButtonStyle, ObjectName
from utils.config.models import ConfigValue

from ..._primitives import make_button
from .._base import BaseDialog
from ._diff import make_diff_cell, split_diff, to_lines
from ._persona_edit import PersonaDiffDialog


class ChangeConfirmDialog(BaseDialog):
    """配置变更二次确认弹窗"""

    def __init__(
        self,
        logs: list[tuple[str, ConfigValue, ConfigValue]],
        persona: tuple[str, str] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent, title=CHANGE_DIALOG.title)
        self.set_always_on_top()
        self.setStyleSheet(build_change_dialog_qss())
        self.setMinimumSize(CHANGE_DIALOG.min_width, CHANGE_DIALOG.min_height)
        self._persona = persona
        self._build_ui(logs)

    @staticmethod
    def confirm(
        logs: list[tuple[str, ConfigValue, ConfigValue]],
        persona: tuple[str, str] | None = None,
        parent: QWidget | None = None,
    ) -> bool:
        """模态展示

        - 返回是否确认保存
        """
        dialog = ChangeConfirmDialog(logs, persona=persona, parent=parent)
        return dialog.exec() == dialog.DialogCode.Accepted

    def _build_ui(self, logs: list[tuple[str, ConfigValue, ConfigValue]]) -> None:
        """提示语 + diff 表格 + 人设行 + 按钮区

        - 只改人设时不出表格，没改人设时不出人设行
        """
        layout = QVBoxLayout(self)
        layout.setSpacing(SETTINGS_DIALOG.tab_spacing)
        tip = QLabel(CHANGE_DIALOG.tip_text)
        layout.addWidget(tip)
        if logs:
            layout.addWidget(self._make_table(logs))
        if self._persona is not None:
            layout.addLayout(self._make_persona_row())
        if not logs:
            # 表格不在场就没人吃空档，补一段拉伸把人设行顶回提示语下面
            layout.addStretch()
        layout.addLayout(self._make_buttons())

    def _make_table(
        self, logs: list[tuple[str, ConfigValue, ConfigValue]]
    ) -> QTableWidget:
        """变更 diff 表格"""
        table = QTableWidget(len(logs), CHANGE_DIALOG.diff_columns)
        table.setObjectName(ObjectName.CHANGE_TABLE)
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

    def _make_persona_row(self) -> QHBoxLayout:
        """人设正文一行，标签加查看变化，摆在表格之外

        - 按钮走人设档样式，不吃表格的悬浮与选中色
        """
        row = QHBoxLayout()
        row.setSpacing(SETTINGS_DIALOG.desc_spacing)
        row.addWidget(QLabel(SETTINGS_DIALOG.persona_label))
        btn_view = make_button(SETTINGS_DIALOG.persona_view_diff, ButtonStyle.PERSONA)
        btn_view.clicked.connect(self._on_view_diff)
        row.addWidget(btn_view)
        row.addStretch()
        return row

    def _on_view_diff(self) -> None:
        """两栏打开人设正文比对"""
        if self._persona is not None:
            PersonaDiffDialog.show_diff(*self._persona, parent=self)

    def _make_buttons(self) -> QHBoxLayout:
        """返回修改 / 确认保存"""
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_cancel = QPushButton(CHANGE_DIALOG.cancel_text)
        btn_cancel.clicked.connect(self.reject)
        btn_ok = make_button(CHANGE_DIALOG.confirm_text, ButtonStyle.PRIMARY)
        btn_ok.clicked.connect(self.accept)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_ok)
        return btn_layout
