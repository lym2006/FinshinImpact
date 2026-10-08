# src/gui/_qss/_dialog.py
"""弹窗样式装配

- 按弹窗组合共用片段与专属表格样式
"""

from .._theme import (
    BODY,
    CHANGE_DIALOG,
    GLOBAL,
    LIST_DIALOG,
    SETTINGS_DIALOG,
    TOOLBAR,
)
from ._parts import (
    DIALOG_BASE_QSS,
    DIALOG_BUTTON_QSS,
    DIALOG_LABEL_QSS,
    DIALOG_QSS,
    LIST_QSS,
    WAIT_QSS,
)

# 变更确认表格
_CHANGE_TABLE_QSS = f"""\
QTableWidget#change_table {{
    background-color: {BODY.bg};
    alternate-background-color: {CHANGE_DIALOG.alt_bg};
    color: {BODY.color};
    border: {SETTINGS_DIALOG.border_width}px solid {SETTINGS_DIALOG.border_color};
    border-radius: {GLOBAL.radius}px;
    gridline-color: {CHANGE_DIALOG.grid_color};
}}

QTableWidget#change_table::item {{
    padding: {LIST_DIALOG.item_padding_v}px {LIST_DIALOG.item_padding_h}px;
}}

QTextEdit#change_cell {{
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

# 检查进度窗表格区（原诊断窗同款，随两窗合并改名）
_CHECK_TABLE_QSS = f"""\
QDialog {{
    background-color: {BODY.bg};
}}

QTextEdit#row_view {{
    background-color: {TOOLBAR.bg};
    color: {BODY.color};
    border: {SETTINGS_DIALOG.border_width}px solid {SETTINGS_DIALOG.border_color};
    border-radius: {GLOBAL.radius}px;
    padding: {SETTINGS_DIALOG.input_padding_v}px {SETTINGS_DIALOG.input_padding_h}px;
}}"""


def build_settings_dialog_qss() -> str:
    """构建弹窗 QSS"""
    return DIALOG_QSS


def build_settings_list_qss() -> str:
    """构建配置列表项 QSS"""
    return LIST_QSS


def build_notice_dialog_qss() -> str:
    """构建通知弹窗 QSS"""
    return "\n".join(
        [
            DIALOG_BASE_QSS,
            DIALOG_LABEL_QSS,
            DIALOG_BUTTON_QSS,
        ]
    )


def build_change_dialog_qss() -> str:
    """构建变更确认弹窗 QSS"""
    return "\n".join(
        [
            DIALOG_BASE_QSS,
            DIALOG_LABEL_QSS,
            DIALOG_BUTTON_QSS,
            _CHANGE_TABLE_QSS,
        ]
    )


def build_wait_dialog_qss() -> str:
    """构建忙碌等待弹窗 QSS"""
    return "\n".join(
        [
            DIALOG_BASE_QSS,
            DIALOG_LABEL_QSS,
            DIALOG_BUTTON_QSS,
            WAIT_QSS,
        ]
    )


def build_check_dialog_qss() -> str:
    """构建检查进度窗 QSS

    - 校验轮与诊断轮共用同一皮肤
    """
    return "\n".join(
        [
            DIALOG_BASE_QSS,
            DIALOG_LABEL_QSS,
            DIALOG_BUTTON_QSS,
            WAIT_QSS,
            _CHECK_TABLE_QSS,
        ]
    )
