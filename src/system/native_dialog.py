"""Win32 原生消息框

- 标题与正文由调用方交来
"""

import ctypes

_MB_ICON_ERROR = 0x10  # 系统报错图标

# 窗上那段异常文本的字数上限，超了截断，长内容只在调试日志里看
_DETAIL_LIMIT = 120


def describe(exc: BaseException) -> str:
    """把异常压成一行短文本

    - 只取类名与消息本体，不带调用链
    - 超长即截断，末尾留省略号
    """
    text = f"{type(exc).__name__}: {exc}"
    return text if len(text) <= _DETAIL_LIMIT else f"{text[:_DETAIL_LIMIT]}…"


def show_error(title: str, body: str) -> None:
    """弹系统级报错框

    - 阻塞到用户关闭
    """
    ctypes.windll.user32.MessageBoxW(0, body, title, _MB_ICON_ERROR)
