# packaging/launch/dialogs.py
"""Win32 弹窗

- 信息、限时、询问、报错四种消息框封装
"""

import ctypes
import sys

from pack_spec import APP_NAME

# Win32 消息框样式与返回值协议
_MB_ICON_INFO = 0x40
_MB_ICON_ERROR = 0x10
_MB_YESNO = 0x04
_ID_YES = 6

_MessageBoxTimeoutW = ctypes.windll.user32.MessageBoxTimeoutW


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


def fail_exit(text: str) -> None:
    """错误弹窗并退出"""
    ctypes.windll.user32.MessageBoxW(0, text, APP_NAME, _MB_ICON_ERROR)
    sys.exit(1)
