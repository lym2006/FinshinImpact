"""任务队列服务

- 存放平台无关的排队与调度
"""

from ._ledger import TaskLedger
from ._queue import TaskItem
from ._service import TaskService, configure_task_service, get_task_service

__all__ = [
    # 排队项
    "TaskItem",
    # 状态账
    "TaskLedger",
    # 服务装配与取用
    "TaskService",
    "configure_task_service",
    "get_task_service",
]
