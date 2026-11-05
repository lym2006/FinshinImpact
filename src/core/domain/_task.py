# src/core/domain/_task.py
"""任务对象

- 定义跨平台归一的任务类型与状态词表
"""

from enum import StrEnum

from ._role import ChatRole

_ChatTurn = tuple[ChatRole, str]
TaskPayload = tuple[_ChatTurn, ...]


class TaskKind(StrEnum):
    """任务类型"""

    CHAT = "chat"


class TaskStatus(StrEnum):
    """任务状态"""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
