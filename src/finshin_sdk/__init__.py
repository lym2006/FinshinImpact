# src/finshin_sdk/__init__.py
"""接口包门面

- 代发插件侧要交的四份声明与处理上下文
- 代发平台侧必须实现的两份抽象接口
- 平台装配的数据形状与探测入口的类型
"""

from ._adapter import BaseAdapter, InteractionPort, RouterBuilder
from ._assembly import AdapterParts, ChannelProbe, PlatformAssembly
from ._context import HandlerContext
from .domain import (
    PlatformTiming,
    PluginRoute,
    PluginSpec,
    PluginTiming,
    TaskHandler,
)

# 接口包自身的版本号，装载前比对适配器清单的接口要求时取它
SDK_VERSION = "0.1.0"

__all__ = [
    # 接口版本
    "SDK_VERSION",
    # 插件契约
    "PluginSpec",
    "PluginRoute",
    "PluginTiming",
    "PlatformTiming",
    "TaskHandler",
    "HandlerContext",
    # 适配器
    "InteractionPort",
    "BaseAdapter",
    "RouterBuilder",
    # 平台装配
    "PlatformAssembly",
    "AdapterParts",
    "ChannelProbe",
]
