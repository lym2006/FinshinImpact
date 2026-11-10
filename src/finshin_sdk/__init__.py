# src/finshin_sdk/__init__.py
"""接口包门面

- 代发插件侧的入口基类与它要交的四份清单
- 代发处理上下文与平台交代的那一份能力
- 代发平台侧必须实现的两份抽象接口
- 平台装配的数据形状与探测入口的类型
"""

from ._adapter import BaseAdapter, InteractionPort, RouterBuilder
from ._assembly import AdapterParts, ChannelProbe, PlatformAssembly
from ._capability import CapabilityCall
from ._context import HandlerContext
from .domain import (
    BackgroundLoop,
    BasePlugin,
    MessageRoute,
    MomentSubscription,
    PlatformMoment,
    QueuedAction,
)

# 接口包自身的版本号，装载前比对适配器清单的接口要求时取它
SDK_VERSION = "0.1.0"

__all__ = [
    # 接口版本
    "SDK_VERSION",
    # 插件契约
    "BasePlugin",
    "MessageRoute",
    "BackgroundLoop",
    "QueuedAction",
    "PlatformMoment",
    "MomentSubscription",
    "HandlerContext",
    "CapabilityCall",
    # 适配器
    "InteractionPort",
    "BaseAdapter",
    "RouterBuilder",
    # 平台装配
    "PlatformAssembly",
    "AdapterParts",
    "ChannelProbe",
]
