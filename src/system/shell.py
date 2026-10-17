# src/system/shell.py
"""桌面打开与窗口激活

- open_path 用系统默认程序打开文件或目录
- activate_explorer 按标题寻找既有资源管理器窗口并置前
"""

import ctypes
import os
import sys
from ctypes import wintypes
from pathlib import Path

# 资源管理器窗口枚举参数
_EXPLORER_CLASSES = {"CabinetWClass", "ExploreWClass"}  # 资源管理器窗口类名
_SW_RESTORE = 9  # 显示并恢复窗口
_WINDOW_TEXT_LEN = 256  # GetClassNameW/GetWindowTextW 缓冲上限


def open_path(target: Path) -> None:
    """用系统默认程序打开文件或目录"""
    if sys.platform != "win32":
        return
    os.startfile(target)


def activate_explorer(title: str) -> bool:
    """激活标题匹配的资源管理器窗口

    - 非 Windows 或未找到一律回 False，调用方决定后续
    """
    if sys.platform != "win32":
        return False

    user32 = ctypes.windll.user32
    found: list[ctypes.c_void_p] = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def _enum(hwnd: wintypes.HWND, _lparam: wintypes.LPARAM) -> bool:
        if not user32.IsWindowVisible(hwnd):
            return True
        cls = ctypes.create_unicode_buffer(_WINDOW_TEXT_LEN)
        user32.GetClassNameW(hwnd, cls, _WINDOW_TEXT_LEN)
        if cls.value not in _EXPLORER_CLASSES:
            return True
        buf = ctypes.create_unicode_buffer(_WINDOW_TEXT_LEN)
        user32.GetWindowTextW(hwnd, buf, _WINDOW_TEXT_LEN)

        # Win11 标题带应用后缀（logs - 文件资源管理器）：取头段比对，全等会漏
        head = buf.value.split(" - ", 1)[0].split(" — ", 1)[0]
        if head == title:
            found.append(hwnd)
            return False
        return True

    user32.EnumWindows(_enum, 0)
    if not found:
        return False
    user32.ShowWindow(found[0], _SW_RESTORE)
    user32.SetForegroundWindow(found[0])
    return True
