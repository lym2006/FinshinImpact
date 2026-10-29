# src/bot/_managers/_signal.py
"""信号处理

- asyncio 线程执行 GUI 信号回调
- 持有应用与人设定稿任务句柄，串行化配置应用防重入
"""

import asyncio
from typing import TYPE_CHECKING

from ui import gui_bridge
from utils import config_manager
from utils.config import load_config

if TYPE_CHECKING:
    from ._manager import BotManager


class SignalHandler:
    """信号处理器

    - 与 BotManager 一对一绑定，全部方法跑在 asyncio 线程
    """

    def __init__(self, host: "BotManager") -> None:
        self._host = host

        # 当前在途的配置应用任务，串行化防重入
        self._apply_task: asyncio.Task[None] | None = None

        # 在途的人设落盘任务，停服时一并取消
        self._commit_task: asyncio.Task[None] | None = None

    def handle_candidate(self) -> None:
        """候选入队"""
        host = self._host
        if host._shutdown:
            host._logger.info("关闭流程中忽略候选校验请求")
            return
        if self._apply_task is not None and not self._apply_task.done():
            host._logger.debug("上一次配置应用尚未完成，跳过本次触发")
            return
        host._applier.skip_reload = True
        self._apply_task = host._loop.create_task(host._applier.apply_config())

    def handle_abort(self) -> None:
        """取消校验

        - 中止进行中的校验，配置回退上次可信值并宣告就绪
        """
        if self._apply_task is not None and not self._apply_task.done():
            self._apply_task.cancel()
        self._host._applier.skip_reload = False
        config_manager.load(load_config())
        gui_bridge.config_ready_changed.emit(True)

    def handle_shutdown_cancel(self) -> None:
        """在事件循环线程复位关闭标志"""
        host = self._host
        if host._shutdown:
            host._logger.info("关闭已取消，恢复配置事件响应")
            host._shutdown = False

    def handle_persona_committed(self, text: str, source: str) -> None:
        """人设正文定稿

        - 关闭流程中不落盘
        """
        host = self._host
        if host._shutdown:
            host._logger.info("关闭流程中忽略人设定稿请求")
            return
        self._commit_task = host._loop.create_task(
            host._applier.commit_persona(text, source)
        )

    def handle_shutdown(self) -> None:
        """停止服务并放行 GUI 退出"""
        host = self._host
        host._logger.info("Manager 收到关闭请求")
        host._shutdown = True
        if self._apply_task is not None and not self._apply_task.done():
            self._apply_task.cancel()
        if self._commit_task is not None and not self._commit_task.done():
            self._commit_task.cancel()
        host.stop_service()
        gui_bridge.shutdown_completed_event.set()
