# src/core/contracts/__init__.py
"""契约门面

- 定义数据存放与插件召唤的出入口
- 只包含抽象接口与能力定义，不放实现
"""

from ._plugin import CapabilityCall
from ._repository import (
    GrantRepository,
    MediaRepository,
    PrincipalRepository,
    SessionRepository,
    TaskRepository,
)

__all__ = [
    # 插件
    "CapabilityCall",
    # 仓储
    "PrincipalRepository",
    "SessionRepository",
    "TaskRepository",
    "MediaRepository",
    "GrantRepository",
]
