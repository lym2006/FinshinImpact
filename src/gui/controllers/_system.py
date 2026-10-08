# src/gui/controllers/_system.py
"""日志控制器

- 提供打开日志目录入口
"""

import ctypes
import os
import sys
from ctypes import wintypes

from utils import LOGS_DIR

from ._base import BaseController

_EXPLORER_CLASSES = {"CabinetWClass", "ExploreWClass"}
_SW_RESTORE = 9


def _activate_explorer(title: str) -> bool:
    """激活标题匹配的资源管理器窗口"""
    user32 = ctypes.windll.user32
    found: list[int] = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def _enum(hwnd, _lparam) -> bool:
        if not user32.IsWindowVisible(hwnd):
            return True
        cls = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, cls, 256)
        if cls.value not in _EXPLORER_CLASSES:
            return True
        buf = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, buf, 256)
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


class LogsController(BaseController):
    """日志控制器"""

    # 契约声明
    LOGGER_NAME = "GUI.Logs"
    BTN_KEY = "log"

    def _execute(self) -> None:
        """打开日志文件所在目录"""
        self.logger.info("正在打开日志文件目录...")
        if sys.platform == "win32":
            try:
                # 成功与置前都不落日志：窗口出现即结果，只留发起与失败
                if not _activate_explorer(LOGS_DIR.name):
                    os.startfile(LOGS_DIR)

            except OSError as e:
                # 路径空格、权限不足、explorer 崩溃等系统级错误统一兜底
                self.logger.send_error("打开日志目录失败", e)

            except Exception as e:
                # 防止任何未知异常导致 GUI 闪退
                self.logger.send_error("发生未知错误", e)
