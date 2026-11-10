# src/core/contracts/__init__.py
"""契约门面

- 定义数据存放的出入口
- 只包含抽象接口，不放实现
"""

from ._repository import (
    GrantRepository,
    MediaRepository,
    PrincipalRepository,
    SessionRepository,
    TaskRepository,
)

__all__ = [
    # 仓储
    "PrincipalRepository",
    "SessionRepository",
    "TaskRepository",
    "MediaRepository",
    "GrantRepository",
]
