# src/system/native_dialog.py
"""Win32 原生消息框

- 给启动最早那段兜底用，此刻界面库可能正是坏掉的那个
- 标题与正文由调用方交来，本模块不引样式与文案层
"""

import ctypes

_MB_ICON_ERROR = 0x10  # 系统报错图标


def show_error(title: str, body: str) -> None:
    """系统级报错弹窗，阻塞到用户点掉"""
    ctypes.windll.user32.MessageBoxW(0, body, title, _MB_ICON_ERROR)
