# src/plugins/AI/core/__init__.py
"""
AI 核心基础组件

导出：
- 网络客户端 (AIClient)
- 会话状态与通用工具
"""

from .chat_context import active_tasks, session_guard, task_queues, user_sessions
from .client import AIClient
from .task import TaskQueue, TaskStoppedError, TelegramTaskItem
from .utils import build_message, get_name, make_data, retry_sending

__all__ = [
    # 网络客户端
    "AIClient",
    # 会话状态管理
    "active_tasks",
    "session_guard",
    "task_queues",
    "user_sessions",
    # 异步任务队列
    "TaskQueue",
    "TaskStoppedError",
    "TelegramTaskItem",
    # 通用工具函数
    "build_message",
    "get_name",
    "make_data",
    "retry_sending",
]
