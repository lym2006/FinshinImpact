# packaging/launch/dialogs.py
"""Win32 弹窗

- 信息、限时、两键询问、三键询问、报错五种消息框封装
"""

import ctypes
import sys
from enum import StrEnum

from pack_spec import APP_NAME

# Win32 消息框样式与返回值协议
_MB_ICON_INFO = 0x40
_MB_ICON_ERROR = 0x10
_MB_YESNO = 0x04
_MB_YESNOCANCEL = 0x03
_ID_YES = 6
_ID_NO = 7
_ID_CANCEL = 2

_MessageBoxTimeoutW = ctypes.windll.user32.MessageBoxTimeoutW


class Answer(StrEnum):
    """三键询问弹窗的按键结果"""

    YES = "yes"
    NO = "no"
    CANCEL = "cancel"


_ANSWER_BY_ID = {_ID_YES: Answer.YES, _ID_NO: Answer.NO, _ID_CANCEL: Answer.CANCEL}


def info(text: str) -> None:
    """信息弹窗"""
    ctypes.windll.user32.MessageBoxW(0, text, APP_NAME, _MB_ICON_INFO)


def wait_info(text: str, ms: int) -> None:
    """限时信息弹窗"""
    _MessageBoxTimeoutW(0, text, APP_NAME, _MB_ICON_INFO, ms, 0)


def ask_yes_no(text: str) -> bool:
    """询问弹窗"""
    flags = _MB_YESNO | _MB_ICON_INFO
    return ctypes.windll.user32.MessageBoxW(0, text, APP_NAME, flags) == _ID_YES


def ask_yes_no_cancel(text: str) -> Answer:
    """三键询问弹窗

    - 按钮固定为是、否、取消，语义由文案交代
    """
    flags = _MB_YESNOCANCEL | _MB_ICON_INFO
    answer = ctypes.windll.user32.MessageBoxW(0, text, APP_NAME, flags)

    # 返回 0 即弹窗创建失败，按取消放行防误升级
    return _ANSWER_BY_ID.get(answer, Answer.CANCEL)


def fail_exit(text: str) -> None:
    """错误弹窗并退出"""
    ctypes.windll.user32.MessageBoxW(0, text, APP_NAME, _MB_ICON_ERROR)
    sys.exit(1)
