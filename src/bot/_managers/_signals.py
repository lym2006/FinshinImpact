# src/bot/_managers/_signals.py
"""信号处理

- asyncio 线程执行 GUI 信号回调
- 持有应用任务句柄，串行化配置应用防重入
"""

import asyncio
from typing import TYPE_CHECKING

from gui.mediator import gui_bridge
from utils import config_manager
from utils.config import load_config

if TYPE_CHECKING:
    from . import BotManager


class SignalHandler:
    """信号处理器

    - 与 BotManager 一对一绑定，全部方法跑在 asyncio 线程
    """

    def __init__(self, host: "BotManager") -> None:
        self._host = host

        # 当前在途的配置应用任务，串行化防重入
        self._apply_task: asyncio.Task[None] | None = None

    def handle_config_saved(self) -> None:
        """重新校验并应用配置"""
        host = self._host
        if host._shutdown:
            host._logger.info("关闭流程中忽略配置保存事件")
            return
        if self._apply_task is not None and not self._apply_task.done():
            host._logger.debug("上一次配置应用尚未完成，跳过本次触发")
            return
        self._apply_task = host._loop.create_task(host._applier.apply_config())

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

        - 中止在途校验，内存回退可信值，当场宣告就绪
        """
        if self._apply_task is not None and not self._apply_task.done():
            self._apply_task.cancel()
        self._host._applier.skip_reload = False
        config_manager.load(load_config())
        gui_bridge.config_ready_changed.emit(True)

    def handle_shutdown_cancel(self) -> None:
        """在 loop 线程复位关闭标志"""
        host = self._host
        if host._shutdown:
            host._logger.info("关闭已取消，恢复配置事件响应")
            host._shutdown = False

    def handle_shutdown(self) -> None:
        """停止服务并放行 GUI 退出"""
        host = self._host
        host._logger.info("Manager 收到关闭请求")
        host._shutdown = True
        if self._apply_task is not None and not self._apply_task.done():
            self._apply_task.cancel()
        host.stop_service()
        gui_bridge.shutdown_completed_event.set()
