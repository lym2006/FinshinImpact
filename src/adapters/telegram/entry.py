# src/adapters/telegram/entry.py
"""Telegram 适配器入口

- 交出装配、探测、预热与诊断四件
"""

from finshin_sdk import AdapterParts, BaseAdapter

from .diagnose import diagnose_flow
from .probe import attempt_channel, preload_engine


def _assemble(token: str, proxy: str | None) -> BaseAdapter:
    """造出 Telegram 的运行时

    - 引擎重依赖在函数体内入场
    """
    # 起主窗不等引擎库，适配器到函数体内才入场
    from .adapter import TelegramAdapter

    return TelegramAdapter(token=token, proxy=proxy)


def parts() -> AdapterParts:
    """交出本适配器入口模块的四件"""
    return AdapterParts(
        assemble=_assemble,
        channel_probe=attempt_channel,
        engine_preload=preload_engine,
        diagnose=diagnose_flow,
    )
