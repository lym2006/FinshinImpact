# src/core/domain/__init__.py
"""领域类型门面

- 定义业务类型，将不同平台的原始类型归一化
- 零外部依赖，不包含实例数据
"""

from ._container import make_container
from ._content import ContentKind
from ._platform import ChatScope, Platform, make_profile_code, platform_of_profile
from ._role import ChatRole, CommandRole
from ._task import TaskKind, TaskPayload, TaskPriority, TaskStatus

__all__ = [
    # 字段创建
    "make_container",
    # 平台
    "Platform",
    "ChatScope",
    # 实例身份码
    "make_profile_code",
    "platform_of_profile",
    # 内容与角色
    "ContentKind",
    "ChatRole",
    "CommandRole",
    # 任务
    "TaskPayload",
    "TaskKind",
    "TaskStatus",
    "TaskPriority",
]
