# src/services/tasks/__init__.py
"""任务队列服务

- 存放平台无关的排队与调度，位于 core 契约与 bundled 之间
- 热队列见 _queue，服务与调度见 _service
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
