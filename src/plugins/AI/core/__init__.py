# src/plugins/AI/core/__init__.py
"""AI 核心门面

- 提供网络客户端与会话状态出口
"""

from ._chat_context import active_tasks, session_guard, task_queues, user_sessions
from ._client import AIClient
from ._tasks import AITaskStoppedError, TaskQueue, TelegramTaskItem

__all__ = [
    # 网络客户端
    "AIClient",
    # 会话状态管理
    "active_tasks",
    "session_guard",
    "task_queues",
    "user_sessions",
    # 异步任务队列
    "AITaskStoppedError",
    "TaskQueue",
    "TelegramTaskItem",
]
