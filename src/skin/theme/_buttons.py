# src/skin/theme/_buttons.py
"""按钮样式名枚举"""

from enum import StrEnum


class ButtonStyle(StrEnum):
    """按钮视觉样式 objectName

    - 改名波及建钮处与各窗 QSS 选择器
    """

    PRIMARY = "btn_primary"
    SECONDARY = "btn_secondary"
    DANGER = "btn_danger"
    START = "btn_start"
    RESET = "btn_reset"
    PERSONA = "btn_persona"
    LIST_ADD = "btn_list_add"
    LIST_DEL = "btn_list_del"
