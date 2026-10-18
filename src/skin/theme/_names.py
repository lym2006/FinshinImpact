# src/skin/theme/_names.py
"""控件对象名词表

- 收创建端 setObjectName 与 QSS 选择器两端共用的对象名
- 按钮类样式名另立 ButtonStyle，本表只收非按钮控件
"""

from enum import StrEnum


class ObjectName(StrEnum):
    """QSS 选择器与控件对象名共用的单源"""

    WAIT_SPINNER = "wait_spinner"
    CHANGE_TABLE = "change_table"
    CHANGE_CELL = "change_cell"
    ROW_VIEW = "row_view"
    LIST_WIDGET = "list_widget"
    PERSONA_PREVIEW = "persona_preview"
    LINK_HEAD = "link_head"
    LINK_TIMER = "link_timer"
    LINK_RETRIES = "link_retries"
