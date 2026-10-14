# packaging/launch/console.py
"""控制台进度窗口

- 分配、回收、驻留三种动作
"""

import ctypes
import sys

_console_open = False


def open_console() -> None:
    """分配控制台窗口

    - 展示安装/升级进度
    """
    global _console_open
    if _console_open:
        return
    ctypes.windll.kernel32.AllocConsole()
    sys.stdout = open("CONOUT$", "w", encoding="oem", errors="replace", buffering=1)
    sys.stderr = sys.stdout
    _console_open = True


def close_console() -> None:
    """回收控制台窗口

    - 主程序拉起后回收窗口
    """
    global _console_open
    if not _console_open:
        return
    ctypes.windll.kernel32.FreeConsole()
    _console_open = False


def hold_console() -> None:
    """驻留进度窗口

    - 供查阅失败详情
    """
    print("\n以上为失败详情，按回车继续…")
    try:
        with open("CONIN$", encoding="oem", errors="replace") as f:
            f.readline()
    except OSError:
        # 输入不可用多半无人值守，直接放行防卡死
        pass
