# src/finshin_sdk/__init__.py
"""适配器接口门面

- 代发平台侧必须实现的两份抽象接口
- 平台装配的数据形状与探测入口的类型
"""

from ._adapter import BaseAdapter, InteractionPort, RouterBuilder
from ._assembly import AdapterParts, ChannelProbe, PlatformAssembly

__all__ = [
    # 适配器
    "InteractionPort",
    "BaseAdapter",
    "RouterBuilder",
    # 平台装配
    "PlatformAssembly",
    "AdapterParts",
    "ChannelProbe",
]
