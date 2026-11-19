"""按钮词表与尺寸档

- 定义按钮的用途词、尺寸档与 objectName 拼法
- 改名波及建钮处与各窗 QSS 选择器
"""

from enum import StrEnum


class ButtonStyle(StrEnum):
    """按钮用途词

    - 成员值即 objectName 主干
    """

    PRIMARY = "btn_primary"
    DANGER = "btn_danger"
    NEUTRAL = "btn_neutral"
    OUTLINE = "btn_outline"
    DELETE = "btn_delete"
    RESET = "btn_reset"
    CONFLICT = "btn_conflict"
    COMMAND = "btn_command"


class ButtonSize(StrEnum):
    """按钮尺寸档

    - 成员值作 objectName 后缀，标准档不缀
    """

    SMALL = "small"
    STANDARD = "standard"
    LARGE = "large"
    COMPACT = "compact"


# 尺寸自成一档的用途词，不随尺寸档换名
_FIXED_SHAPED = frozenset(
    {ButtonStyle.RESET, ButtonStyle.CONFLICT, ButtonStyle.COMMAND}
)


def button_object_name(style: ButtonStyle, size: ButtonSize) -> str:
    """按钮 objectName

    - 标准档与固定形状取词本身
    - 其余档拼上尺寸后缀
    """
    if size is ButtonSize.STANDARD or style in _FIXED_SHAPED:
        return style
    return f"{style}_{size}"
