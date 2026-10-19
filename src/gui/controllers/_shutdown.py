# src/gui/controllers/_shutdown.py
"""关闭控制器（内部实现）

- 实现退出流程调度
- 实现关闭与配置弹窗竞态协调
"""

import os

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QDialog, QWidget

from ..dialogs import ShutdownDialog
from ..mediator import gui_bridge
from ._base import BaseController
from ._decorator import gui_guard


class ShutdownController(BaseController):
    """进程关闭控制器"""

    # ==================== 契约声明 ====================

    LOGGER_NAME = "GUI.Shutdown"
    BTN_KEY = "shutdown"

    # ==================== 初始化 ====================

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._check_shutdown_timer: QTimer = None  # type: ignore
        self._force_exit_timer: QTimer = None  # type: ignore
        self._is_shutting_down = False

    def _execute(self) -> None:
        """执行退出逻辑"""
        self._on_close_intercepted()

    @gui_guard
    def request_exit_from(self, source: QWidget | None = None) -> None:
        """响应向导的退出请求

        确认框以向导为父级盖在其上，取消后向导与已填内容原样保留。
        """
        self._on_close_intercepted(source)

    def shutdown_now(self) -> None:
        """跳过确认直接退出

        致命错误确认后调用。
        """
        if self._is_shutting_down:
            return
        gui_bridge.set_shutdown_pending(True)
        self.logger.info("用户确认致命提示，直接退出")
        self._start_shutdown()

    def _on_close_intercepted(self, source: QWidget | None = None) -> None:
        """弹出确认框，确认后启动清理流程"""
        # 不重复执行
        if self._is_shutting_down:
            return

        # 在弹出确认框之前标记关闭意向，阻止关闭期间再弹强制配置
        gui_bridge.set_shutdown_pending(True)
        dialog = ShutdownDialog(parent=source or self.gui)
        reply = dialog.exec()

        if reply == dialog.DialogCode.Accepted:
            self.logger.info("用户确认退出，开始清理资源...")

            # 来源是向导时一并关闭：退出已确认，向导无需再驻留
            if isinstance(source, QDialog):
                source.accept()
            self._start_shutdown()

        else:
            self.logger.info("用户取消关闭操作")
            self._is_shutting_down = False
            gui_bridge.set_shutdown_pending(False)
            gui_bridge.shutdown_completed_event.clear()
            gui_bridge.request_shutdown_cancel.emit()
            self._stop_timers()

    def _start_shutdown(self) -> None:
        self._is_shutting_down = True
        gui_bridge.request_shutdown.emit()

        # 检查定时器：每 0.1 秒轮询底层清理状态
        self.logger.info("正在等待 Bot 线程清理资源...")
        self._check_shutdown_timer = QTimer(self.gui)
        self._check_shutdown_timer.timeout.connect(self._check_shutdown_status)
        self._check_shutdown_timer.start(100)
        self.logger.debug("检查定时器已启动，轮询间隔 0.1 秒")

        # 超时定时器：如果 5 秒后还没清理完，强行退出
        self._force_exit_timer = QTimer(self.gui)
        self._force_exit_timer.setSingleShot(True)
        self._force_exit_timer.timeout.connect(self._force_exit)
        self._force_exit_timer.start(5000)
        self.logger.debug("超时定时器已启动，5 秒后未清理完则强制退出")

    def _check_shutdown_status(self) -> None:
        """轮询检查 Bot 线程是否清理完毕"""
        # 用户取消清理，不检查
        if not self._is_shutting_down:
            return

        if gui_bridge.shutdown_completed_event.is_set():
            # 停掉定时器与超时定时器（如果有）
            self._stop_timers()
            self.logger.info("资源清理完成，1 秒后退出...")
            QTimer.singleShot(1000, lambda: os._exit(0))

    def _force_exit(self) -> None:
        """超时强制退出"""
        # 取消或已完成时直接放行
        if not self._is_shutting_down or gui_bridge.shutdown_completed_event.is_set():
            return
        self.logger.error("清理超时，强制终止进程")
        os._exit(1)  # 返回非零退出码，表示异常退出

    def _stop_timers(self) -> None:
        """停掉所有定时器"""
        if self._check_shutdown_timer:
            self._check_shutdown_timer.stop()
        if self._force_exit_timer:
            self._force_exit_timer.stop()
