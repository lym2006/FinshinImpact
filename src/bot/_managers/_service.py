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
    from core.domain import PluginBackground, PluginReset

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
        from .._service import BotService

        self.stop_service()  # 停掉旧服务（如果有）

        self.logger.info(EngineMessage.CREATING)
        adapter, backgrounds, resets = self._create_components()
        self._history_resets = resets
        self._service = BotService(adapter, backgrounds)

        await asyncio.to_thread(self._service.start)
        self.logger.info(EngineMessage.STARTED)

    def _create_components(
        self,
    ) -> tuple[TelegramAdapter, tuple[PluginBackground, ...], tuple[PluginReset, ...]]:
        """按配置构建适配器、插件常驻协程与历史清理入口

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
        report, backgrounds, resets = register_plugins(dispatcher, build_router)
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

        return adapter, backgrounds, resets

    def stop_service(self) -> None:
        """停止 Bot 服务"""
        if not self._service:
            return
        self.logger.info(EngineMessage.STOPPING)
        service = self._service
        self._service = None
        service.stop()
