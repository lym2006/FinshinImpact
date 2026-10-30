# src/bot/_managers/_service.py
"""服务管理器

- 实现 BotService 生命周期管理
- 提供组件构建与停止清理入口
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import TYPE_CHECKING

from skin.messages import EngineMessage

from ._base import BaseManager

if TYPE_CHECKING:
    from adapters.telegram.adapter import TelegramAdapter
    from core.domain import PluginBackground, PluginReset, PluginStartup, TaskHandler
    from services.tasks import TaskItem

    from .._service import BotService


class ServiceManager(BaseManager):
    """服务管理器"""

    LOGGER_NAME = "Service"

    def __init__(
        self,
        get_config_func: Callable[[], tuple[str, str]],
    ) -> None:
        super().__init__()
        self._get_config = get_config_func
        self._service: BotService | None = None

        # 插件交出的历史清理入口，随本次注册收集
        self._history_resets: tuple[PluginReset, ...] = ()

    @property
    def history_resets(self) -> tuple[PluginReset, ...]:
        """当前这套插件的历史清理入口"""
        return self._history_resets

    async def _execute(self) -> None:
        """启动 Bot 服务"""
        from services.tasks import TaskLedger, configure_task_service
        from utils.paths import DB_FILE

        from .._service import BotService

        self.stop_service()  # 停掉旧服务（如果有）

        self.logger.info(EngineMessage.CREATING)
        adapter, backgrounds, resets, handlers, startups = self._create_components()
        self._history_resets = resets
        configure_task_service(
            handlers,
            ledger=TaskLedger(DB_FILE, on_fault=self._report_ledger_fault),
            on_fault=self._report_task_fault,
        )
        self._service = BotService(adapter, backgrounds, startups)

        await asyncio.to_thread(self._service.start)
        self.logger.info(EngineMessage.STARTED)

    def _create_components(
        self,
    ) -> tuple[
        TelegramAdapter,
        tuple[PluginBackground, ...],
        tuple[PluginReset, ...],
        tuple[TaskHandler, ...],
        tuple[PluginStartup, ...],
    ]:
        """按配置构建适配器、插件常驻协程、历史清理入口、任务处理清单与启动交代协程

        - aiogram 重依赖此刻才入场，主窗启动不受其拖累
        """
        from adapters.telegram.adapter import TelegramAdapter
        from adapters.telegram.router_bridge import build_router
        from utils.middleware import LoggingMiddleware
        from utils.plugin import register_plugins

        token, proxy = self._get_config()
        adapter = TelegramAdapter(token=token, proxy=proxy)
        dispatcher = adapter.dispatcher

        # 注册中间件和路由
        dispatcher.update.outer_middleware(LoggingMiddleware())
        report, backgrounds, resets, handlers, startups = register_plugins(
            dispatcher, build_router
        )
        total = len(report)
        self.logger.info(EngineMessage.PLUGINS_DONE.format(n=total))
        for index, (name, ok, reason) in enumerate(report, 1):
            if ok:
                self.logger.info(
                    EngineMessage.PLUGIN_OK.format(index=index, n=total, name=name)
                )
            else:
                self.logger.error(
                    EngineMessage.PLUGIN_FAIL.format(
                        index=index, n=total, name=name, reason=reason
                    )
                )

        return adapter, backgrounds, resets, handlers, startups

    def _report_task_fault(self, item: TaskItem, error: Exception) -> None:
        """任务派发失败的行落在面板"""
        self.logger.error(EngineMessage.TASK_FAULT.format(kind=item.kind, reason=error))

    def _report_ledger_fault(self, item: TaskItem, error: Exception) -> None:
        """状态账写失败的行落在面板

        - 账本断头不拦派发，回答照走
        """
        self.logger.error(
            EngineMessage.TASK_LEDGER_FAULT.format(kind=item.kind, reason=error)
        )

    def stop_service(self) -> None:
        """停止 Bot 服务"""
        if not self._service:
            return
        self.logger.info(EngineMessage.STOPPING)
        service = self._service
        self._service = None
        service.stop()
