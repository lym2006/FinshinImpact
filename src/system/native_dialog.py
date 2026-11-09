# src/system/native_dialog.py
"""Win32 原生消息框

- 给启动最早那段兜底用，此刻界面库可能正是坏掉的那个
- 标题与正文由调用方交来，本模块不引样式与文案层
"""

import ctypes

_MB_ICON_ERROR = 0x10  # 系统报错图标

# 窗上那段异常文本的字数上限，超了截断，长内容只在调试日志里看
_DETAIL_LIMIT = 120


def describe(exc: BaseException) -> str:
    """把异常缩成窗上读得下的一行

    - 只到类名与消息本体，调用链不在此处
    - 超长即截断，末尾留省略号
    """
    text = f"{type(exc).__name__}: {exc}"
    return text if len(text) <= _DETAIL_LIMIT else f"{text[:_DETAIL_LIMIT]}…"


def show_error(title: str, body: str) -> None:
    """系统级报错弹窗，阻塞到用户点掉"""
    ctypes.windll.user32.MessageBoxW(0, body, title, _MB_ICON_ERROR)
