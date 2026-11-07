# src/bot/_managers/_service.py
"""服务管理器

- 引擎运行时的生命周期管理
- 组件构建、插件时机订阅与停止清理入口
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING

from core.contracts import CapabilityCall
from core.domain import ContentKind, PlatformTiming
from core.dto import OutboundPayloadDTO, PluginManifestDTO
from exceptions import MAP_KEY_PLUGINS, MAPS, BotError
from finshin_sdk import PlatformAssembly
from skin.messages import EngineMessage
from utils.paths import PLATFORM

from .._adapter_host import assemble_platform
from ._base import BaseManager

if TYPE_CHECKING:
    from core.domain import PluginTimingRun
    from core.dto import PrincipalDTO
    from services.tasks import TaskItem

    from .._service import AdapterRuntime

_ERR_MAP_PLUGIN = MAPS[MAP_KEY_PLUGINS]


def _failure_reason(error: BaseException) -> str:
    """失败行的原因取映射文案

    - 认得出的异常族照映射填
    - 认不出的报异常类名，细节归调试日志
    """
    template = _ERR_MAP_PLUGIN.get(type(error)) if isinstance(error, BotError) else None
    if template is None:
        return type(error).__name__
    return template.format(**vars(error))


class ServiceManager(BaseManager):
    """服务管理器"""

    LOGGER_NAME = "Service"

    def __init__(
        self,
        get_config_func: Callable[[], tuple[str, str]],
    ) -> None:
        super().__init__()
        self._get_config = get_config_func
        self._service: AdapterRuntime | None = None

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

        from .._service import AdapterRuntime

        self.stop_service()  # 停掉旧服务（如果有）

        self.logger.debug(EngineMessage.CREATING)
        parts = self._create_components()
        self._timing_hooks = parts.timings
        self._log_plugin_report(parts.report)
        configure_task_service(
            parts.handlers,
            ledger=TaskLedger(DB_FILE, on_fault=self._report_ledger_fault),
            on_fault=self._report_task_fault,
        )
        self._service = AdapterRuntime(
            parts.adapter,
            self.capability_call(),
            parts.backgrounds,
            self.hooks_for(PlatformTiming.BEFORE_ENGINE_RUN),
        )

        await asyncio.to_thread(self._service.start)
        self.logger.debug(EngineMessage.STARTED)

    def _create_components(self) -> PlatformAssembly:
        """按配置装配本实例平台的适配器与插件清单"""
        token, proxy = self._get_config()
        return assemble_platform(PLATFORM, token, proxy)

    def _log_plugin_report(
        self, report: Sequence[tuple[PluginManifestDTO, Exception | None]]
    ) -> None:
        """逐条落插件加载结果，失败行带映射文案

        - 成功行报导入路径，看得出这只插件来自哪一根目录
        """
        total = len(report)
        self.logger.info(EngineMessage.PLUGINS_DONE.format(n=total))
        for index, (manifest, error) in enumerate(report, 1):
            if error is None:
                self.logger.debug(
                    EngineMessage.PLUGIN_OK.format(
                        index=index, n=total, module=manifest.module
                    )
                )
                continue
            self.logger.send_error(
                EngineMessage.PLUGIN_FAIL.format(
                    index=index,
                    n=total,
                    name=manifest.name,
                    reason=_failure_reason(error),
                ),
                error,
            )

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
