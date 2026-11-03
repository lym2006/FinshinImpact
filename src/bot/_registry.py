# src/bot/_registry.py
"""平台装配登记

- 定义各平台的适配器装配、单通道探测、引擎预热与诊断入口
- 上层按平台标识取件，取到才导入对应平台包
"""

from collections.abc import Awaitable, Callable, Coroutine
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from adapters.telegram.diagnose import diagnose_flow
from adapters.telegram.probe import attempt_channel, preload_engine
from core.domain import (
    Platform,
    PlatformTiming,
    PluginBackground,
    PluginTimingRun,
    TaskHandler,
)
from exceptions import PluginsError
from utils.plugin import register_plugins

if TYPE_CHECKING:
    from core.contracts import BaseAdapter

# 单通道探测：收 token 与代理，回生效代理与该通道的字段错误
_ChannelProbe = Callable[[str, str], Awaitable[tuple[str | None, dict[str, str]]]]

# 一轮网络诊断，收配置代理、token 与代理模式，逐帧回调并按停止判定中止
_DiagnoseFlow = Callable[..., Coroutine[Any, Any, None]]


@dataclass(frozen=True, slots=True)
class PlatformAssembly:
    """一个平台装配出来的件

    - 适配器交运行时托管，其余四件交装配层登记
    """

    adapter: "BaseAdapter"
    report: list[tuple[str, PluginsError | None]]
    backgrounds: tuple[PluginBackground, ...]
    handlers: tuple[TaskHandler, ...]
    timings: dict[PlatformTiming, tuple[PluginTimingRun, ...]]


@dataclass(frozen=True, slots=True)
class _PlatformEntry:
    """一个平台的装配件"""

    assemble: Callable[[str, str | None], PlatformAssembly]
    channel_probe: _ChannelProbe
    engine_preload: Callable[[], None]
    diagnose: _DiagnoseFlow


def _assemble_telegram(token: str, proxy: str | None) -> PlatformAssembly:
    """装配 Telegram 平台的件

    - 引擎重依赖在函数体内入场，主窗启动不等它
    """
    from adapters.telegram.adapter import TelegramAdapter
    from adapters.telegram.router_bridge import build_router
    from utils.middleware import LoggingMiddleware

    adapter = TelegramAdapter(token=token, proxy=proxy)
    dispatcher = adapter.dispatcher

    dispatcher.update.outer_middleware(LoggingMiddleware())
    report, backgrounds, handlers, timings = register_plugins(dispatcher, build_router)
    return PlatformAssembly(adapter, report, backgrounds, handlers, timings)


# 平台标识到装配件，一条平台一行
_ENTRIES: dict[Platform, _PlatformEntry] = {
    Platform.TELEGRAM: _PlatformEntry(
        assemble=_assemble_telegram,
        channel_probe=attempt_channel,
        engine_preload=preload_engine,
        diagnose=diagnose_flow,
    )
}


def entry_for(platform: Platform) -> _PlatformEntry:
    """按平台标识取装配件"""
    return _ENTRIES[platform]
