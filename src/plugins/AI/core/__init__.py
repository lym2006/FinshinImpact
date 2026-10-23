# src/plugins/AI/core/__init__.py
"""AI 核心门面

- 提供网络客户端、会话状态与落库出口
"""

from ._chat_context import active_tasks, session_guard, session_states, task_queues
from ._client import AIClient
from ._store import (
    clear_session,
    purge_history,
    purge_idle_sessions,
    read_session,
    save_session,
)
from ._tasks import TaskQueue

__all__ = [
    # 网络客户端
    "AIClient",
    # 会话状态管理
    "active_tasks",
    "session_guard",
    "session_states",
    "task_queues",
    # 异步任务队列
    "TaskQueue",
    # 会话落库
    "clear_session",
    "purge_history",
    "purge_idle_sessions",
    "read_session",
    "save_session",
]
