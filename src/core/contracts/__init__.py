# src/core/contracts/__init__.py
"""契约门面

- 定义核心业务与外部平台、数据存放、插件召唤的出入口
- 只包含抽象接口与能力定义，不放实现
"""

from ._adapter import BaseAdapter, InteractionPort
from ._plugin import CapabilityCall
from ._repository import (
    GrantRepository,
    MediaRepository,
    PrincipalRepository,
    SessionRepository,
    TaskRepository,
)

__all__ = [
    # 适配器
    "InteractionPort",
    "BaseAdapter",
    # 插件
    "CapabilityCall",
    # 仓储
    "PrincipalRepository",
    "SessionRepository",
    "TaskRepository",
    "MediaRepository",
    "GrantRepository",
]
