# src/plugins/AI/core/__init__.py
"""AI 核心门面

- 提供网络客户端、会话状态、落库与命令授权出口
"""

from ._access import require_role
from ._chat_context import active_tasks, session_guard, session_states, task_queues
from ._client import AIClient
from ._grants import add_admin, remove_admin
from ._store import (
    clear_session,
    purge_history,
    purge_idle_sessions,
    read_session,
    save_session,
    save_summary,
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
    # 命令权限与授权
    "add_admin",
    "remove_admin",
    "require_role",
    # 异步任务队列
    "TaskQueue",
    # 会话落库
    "clear_session",
    "purge_history",
    "purge_idle_sessions",
    "read_session",
    "save_session",
    "save_summary",
]
