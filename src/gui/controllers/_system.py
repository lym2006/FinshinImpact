# src/gui/controllers/_system.py
"""系统控制器（内部实现）

- 提供日志目录、配置与版本检查入口
"""

import asyncio
import ctypes
import os
import sys
from ctypes import wintypes

from PySide6.QtCore import QThread, Signal

from exceptions import MAPS, VersionError
from utils import LOGS_DIR, check_updates

from .._theme import WAIT_DIALOG as PD
from ..dialogs import WaitDialog
from ._base import BaseController

_EXPLORER_CLASSES = {"CabinetWClass", "ExploreWClass"}
_SW_RESTORE = 9


def _activate_explorer(title: str) -> bool:
    """激活标题匹配的资源管理器窗口"""
    if sys.platform != "win32":
        return False
    user32 = ctypes.windll.user32
    found: list[int] = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def _enum(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        cls = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, cls, 256)
        if cls.value not in _EXPLORER_CLASSES:
            return True
        buf = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, buf, 256)
        if buf.value == title:
            found.append(hwnd)
            return False
        return True

    user32.EnumWindows(_enum, 0)
    if not found:
        return False
    user32.ShowWindow(found[0], _SW_RESTORE)
    user32.SetForegroundWindow(found[0])
    return True


_ERR_MAP = MAPS["Init"]["Version"]


class LogsController(BaseController):
    """日志控制器"""

    # ==================== 契约声明 ====================

    LOGGER_NAME = "GUI.Logs"
    BTN_KEY = "log"

    # ==================== 业务逻辑实现 ====================

    def _execute(self) -> None:
        """打开日志文件所在目录"""
        self.logger.info("正在打开日志文件目录...")
        if sys.platform == "win32":
            try:
                if _activate_explorer(LOGS_DIR.name):
                    self.logger.info("日志目录已打开，置前显示")
                    return
                os.startfile(LOGS_DIR)
                self.logger.info("成功打开日志目录")

            except OSError as e:
                # 路径空格、权限不足、explorer 崩溃等系统级错误统一兜底
                self.logger.send_error("打开日志目录失败", e)

            except Exception as e:
                # 防止任何未知异常导致 GUI 闪退
                self.logger.send_error("发生未知错误", e)


class _UpdateWorker(QThread):
    """版本检查线程：网络探测不占 GUI 线程

    线程内 asyncio.run 建一次性 loop 跑协程；结果以 (文案, 成败) 发回，
    控件更新由 Qt 排队投递回主线程，本线程绝不碰控件。
    """

    done = Signal(str, bool)

    def run(self) -> None:
        try:
            ver = asyncio.run(check_updates())
            self.done.emit(PD.up_to_date.format(ver=ver), True)
        except VersionError as e:
            self.done.emit(_ERR_MAP[type(e)].format(**vars(e)), False)
        except Exception as e:
            self.done.emit(f"版本检查异常：{type(e).__name__}", False)


class UpdateController(BaseController):
    """更新控制器"""

    # ==================== 契约声明 ====================

    LOGGER_NAME = "GUI.Version"
    BTN_KEY = "update"

    def _execute(self) -> None:
        """检查版本更新

        模态转圈，结果经用户确认后关闭；网络活在临时线程。
        """
        dialog = WaitDialog(PD.check_text, parent=self.gui)
        worker = _UpdateWorker()

        # 线程挂主窗：用户提前关窗后仍被持有，防运行中被 GC 析构崩溃
        worker.setParent(self.gui)
        worker.done.connect(dialog.finish)
        worker.done.connect(
            lambda msg, passed: (
                self.logger.info(f"版本检查：{msg}")
                if passed
                else self.logger.error(f"版本检查失败：{msg}")
            )
        )
        worker.finished.connect(worker.deleteLater)
        worker.start()
        dialog.exec()
