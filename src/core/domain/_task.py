# src/core/domain/_task.py
"""任务对象

- 定义跨平台归一的任务类型、状态与优先级词表
"""

from enum import IntEnum, StrEnum

from ._role import ChatRole

_ChatTurn = tuple[ChatRole, str]
TaskPayload = tuple[_ChatTurn, ...]


class TaskKind(StrEnum):
    """任务类型"""

    # 通用
    CHAT = "chat"

    # 特权
    MD = "md"
    CLEAR = "clear"
    DELETE = "delete"
    HISTORY = "history"


class TaskStatus(StrEnum):
    """任务状态"""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    CANCELLED = "cancelled"
    FAILED = "failed"


class TaskPriority(IntEnum):
    """任务优先级

    - 数值越小越优先
    """

    IMMEDIATE = 0  # 指令类：clear、delete
    HIGH = 10  # 查询类：md、history
    NORMAL = 50  # 普通对话：chat
