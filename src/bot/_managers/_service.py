# src/bot/_managers/_service.py
"""服务管理器

- BotService 生命周期管理
- 组件构建、插件时机订阅与停止清理入口
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import TYPE_CHECKING

from core.contracts import CapabilityCall
from core.domain import ContentKind, PlatformTiming
from core.dto import OutboundPayloadDTO
from exceptions import MAP_KEY_PLUGINS, MAPS
from skin.messages import EngineMessage

from ._base import BaseManager

if TYPE_CHECKING:
    from adapters.telegram.adapter import TelegramAdapter
    from core.domain import PluginBackground, PluginTimingRun, TaskHandler
    from core.dto import PrincipalDTO
    from services.tasks import TaskItem

    from .._service import BotService

_ERR_MAP_PLUGIN = MAPS[MAP_KEY_PLUGINS]


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

        # 插件订阅的平台机会，随本次注册收集
        self._timing_hooks: dict[PlatformTiming, tuple[PluginTimingRun, ...]] = {}

    def hooks_for(self, timing: PlatformTiming) -> tuple[PluginTimingRun, ...]:
        """订阅了这个平台时机的件，按交出的先后排"""
        return self._timing_hooks.get(timing, ())

    def capability_call(self) -> CapabilityCall:
        """召唤插件时交代的那份能力

        - 说话走当时在跑的服务，插件碰不到发出去的那条消息长什么样
        """
        return CapabilityCall(say=self._say)

    async def _say(self, principal: PrincipalDTO, text: str) -> None:
        """把一句话拼成文本消息交给当前服务的出口"""
        if self._service is None:
            raise RuntimeError("服务未启动，插件要说话没有出口")
        payload = OutboundPayloadDTO(kind=ContentKind.TEXT, text=text)
        await self._service.interaction.send_message(principal, payload)

    async def _execute(self) -> None:
        """启动 Bot 服务"""
        from services.tasks import TaskLedger, configure_task_service
        from utils.paths import DB_FILE

        from .._service import BotService

        self.stop_service()  # 停掉旧服务（如果有）

        self.logger.debug(EngineMessage.CREATING)
        adapter, backgrounds, handlers, timing_hooks = self._create_components()
        self._timing_hooks = timing_hooks
        configure_task_service(
            handlers,
            ledger=TaskLedger(DB_FILE, on_fault=self._report_ledger_fault),
            on_fault=self._report_task_fault,
        )
        self._service = BotService(
            adapter,
            self.capability_call(),
            backgrounds,
            self.hooks_for(PlatformTiming.BEFORE_ENGINE_RUN),
        )

        await asyncio.to_thread(self._service.start)
        self.logger.debug(EngineMessage.STARTED)

    def _create_components(
        self,
    ) -> tuple[
        TelegramAdapter,
        tuple[PluginBackground, ...],
        tuple[TaskHandler, ...],
        dict[PlatformTiming, tuple[PluginTimingRun, ...]],
    ]:
        """按配置构建适配器、插件常驻协程、任务处理清单与按时机归组的订阅

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
        report, backgrounds, handlers, timing_hooks = register_plugins(
            dispatcher, build_router
        )
        total = len(report)
        self.logger.info(EngineMessage.PLUGINS_DONE.format(n=total))
        for index, (name, error) in enumerate(report, 1):
            if error is None:
                self.logger.debug(
                    EngineMessage.PLUGIN_OK.format(index=index, n=total, name=name)
                )
                continue
            self.logger.send_error(
                EngineMessage.PLUGIN_FAIL.format(
                    index=index,
                    n=total,
                    name=name,
                    reason=_ERR_MAP_PLUGIN[type(error)].format(**vars(error)),
                ),
                error,
            )

        return adapter, backgrounds, handlers, timing_hooks

    def _report_task_fault(self, item: TaskItem, error: Exception) -> None:
        """任务派发失败的行落在面板，异常本体下沉调试日志"""
        self.logger.send_error(EngineMessage.TASK_FAULT.format(kind=item.kind), error)

    def _report_ledger_fault(self, item: TaskItem, error: Exception) -> None:
        """状态账写失败的行落在面板

        - 账本断头不拦派发，回答照走
        - 异常本体下沉调试日志
        """
        self.logger.send_error(
            EngineMessage.TASK_LEDGER_FAULT.format(kind=item.kind), error
        )

    def stop_service(self) -> None:
        """停止 Bot 服务"""
        if not self._service:
            return
        self.logger.debug(EngineMessage.STOPPING)
        service = self._service
        self._service = None
        service.stop()
