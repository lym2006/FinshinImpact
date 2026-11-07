# src/adapters/telegram/entry.py
"""Telegram 适配器入口

- 交出装配、探测、预热与诊断四件
"""

from finshin_sdk import AdapterParts, PlatformAssembly

from .diagnose import diagnose_flow
from .probe import attempt_channel, preload_engine


def _assemble(token: str, proxy: str | None) -> PlatformAssembly:
    """装配 Telegram 平台的件

    - 引擎重依赖在函数体内入场，主窗启动不等它
    """
    from utils.middleware import LoggingMiddleware
    from utils.plugin import register_plugins

    from .adapter import TelegramAdapter
    from .router_bridge import build_router

    adapter = TelegramAdapter(token=token, proxy=proxy)
    dispatcher = adapter.dispatcher

    dispatcher.update.outer_middleware(LoggingMiddleware())
    report, backgrounds, handlers, timings = register_plugins(dispatcher, build_router)
    return PlatformAssembly(adapter, report, backgrounds, handlers, timings)


def parts() -> AdapterParts:
    """交出本适配器入口模块的四件"""
    return AdapterParts(
        assemble=_assemble,
        channel_probe=attempt_channel,
        engine_preload=preload_engine,
        diagnose=diagnose_flow,
    )
