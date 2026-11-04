# src/skin/qss/_business.py
"""业务弹窗 QSS 拼装

- 收纳变更确认与检查进度两类表格片段
- 校验态文字串供字段标签逐控件贴色
- 配置弹窗与列表片段在同目录的配置模块里
"""

from ..theme import (
    BODY,
    CHANGE_DIALOG,
    GLOBAL,
    LIST_DIALOG,
    SETTINGS_DIALOG,
    TOOLBAR,
    ObjectName,
)
from ._base import WAIT_QSS, Qss, with_dialog_base

# 字段校验态文字
_ERROR_LABEL_QSS = f"color: {SETTINGS_DIALOG.error_color};"
_PENDING_LABEL_QSS = f"color: {SETTINGS_DIALOG.pending_color};"

# 变更确认表格
_CHANGE_TABLE_QSS = f"""\
QTableWidget#{ObjectName.CHANGE_TABLE} {{
    background-color: {BODY.bg};
    alternate-background-color: {CHANGE_DIALOG.alt_bg};
    color: {BODY.color};
    border: {SETTINGS_DIALOG.border_width}px solid {SETTINGS_DIALOG.border_color};
    border-radius: {GLOBAL.radius}px;
    gridline-color: {CHANGE_DIALOG.grid_color};
}}

QTableWidget#{ObjectName.CHANGE_TABLE}::item {{
    padding: {LIST_DIALOG.item_padding_v}px {LIST_DIALOG.item_padding_h}px;
}}

QTextEdit#{ObjectName.CHANGE_CELL} {{
    background-color: {CHANGE_DIALOG.alt_bg};
    color: {BODY.color};
    border: none;
    padding: {CHANGE_DIALOG.cell_padding_v}px {CHANGE_DIALOG.cell_padding_h}px;
}}

QHeaderView::section {{
    background-color: {SETTINGS_DIALOG.tab_bg};
    color: {BODY.hover_color};
    border: none;
    padding: {LIST_DIALOG.item_padding_v}px {LIST_DIALOG.item_padding_h}px;
}}"""

# 检查进度窗表格区
_CHECK_TABLE_QSS = f"""\
QDialog {{
    background-color: {BODY.bg};
}}

QTextEdit#{ObjectName.ROW_VIEW} {{
    background-color: {TOOLBAR.bg};
    color: {BODY.color};
    border: {SETTINGS_DIALOG.border_width}px solid {SETTINGS_DIALOG.border_color};
    border-radius: {GLOBAL.radius}px;
    padding: {SETTINGS_DIALOG.input_padding_v}px {SETTINGS_DIALOG.input_padding_h}px;
}}"""


def build_change_dialog_qss() -> Qss:
    """构建变更确认弹窗 QSS"""
    return with_dialog_base(_CHANGE_TABLE_QSS)


def build_check_dialog_qss() -> Qss:
    """构建检查进度窗 QSS

    - 校验轮与诊断轮共用同一皮肤
    """
    return with_dialog_base(WAIT_QSS, _CHECK_TABLE_QSS)


def build_error_label_qss() -> Qss:
    """构建字段标红串"""
    return Qss(_ERROR_LABEL_QSS)


def build_pending_label_qss() -> Qss:
    """构建字段待检串"""
    return Qss(_PENDING_LABEL_QSS)
