"""QSS 基础件

- Qss 串类型与各弹窗共用的通用片段
- 基础与标签样式打头，按钮规则一律取自按钮唯一出处
"""

from typing import NewType

from ..theme import BODY, SETTINGS_DIALOG, WAIT_DIALOG, ObjectName
from ._buttons import build_button_qss

# 装配完成的 QSS 串，各弹窗成品串的出口类型
Qss = NewType("Qss", str)

# 弹窗基本样式
DIALOG_BASE_QSS = f"""\
QDialog {{
    background-color: {BODY.bg};
}}"""

# 标题
DIALOG_LABEL_QSS = f"""\
QLabel {{
    color: {BODY.color};
}}"""

# 人设预览区
DIALOG_PREVIEW_QSS = f"""\
QTextEdit#{ObjectName.PERSONA_PREVIEW} {{
    background-color: {SETTINGS_DIALOG.tab_bg};
}}"""

# 忙碌等待弹窗
WAIT_QSS = f"""\
QLabel#{ObjectName.WAIT_SPINNER} {{
    font-size: {WAIT_DIALOG.spinner_font_size}px;
    color: {WAIT_DIALOG.spinner_color};
}}"""


def with_dialog_base(*tail: str) -> Qss:
    """拼装弹窗 QSS"""
    return Qss(
        "\n".join(
            [
                DIALOG_BASE_QSS,
                DIALOG_LABEL_QSS,
                DIALOG_PREVIEW_QSS,
                build_button_qss(),
                *tail,
            ]
        )
    )
