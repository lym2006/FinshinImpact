# src/plugins/AI/core/__init__.py
"""AI 核心门面

- 提供网络客户端、会话状态与落库出口
"""

from ._chat_context import active_tasks, session_guard, session_states
from ._client import AIClient, StreamUsage
from ._store import (
    clear_session,
    purge_history,
    purge_idle_sessions,
    purge_pending,
    purge_sessions,
    purge_stale,
    read_session,
    save_session,
    save_summary,
)

__all__ = [
    # 网络客户端
    "AIClient",
    "StreamUsage",
    # 会话状态管理
    "active_tasks",
    "session_guard",
    "session_states",
    # 会话落库
    "clear_session",
    "purge_history",
    "purge_idle_sessions",
    "purge_pending",
    "purge_sessions",
    "purge_stale",
    "read_session",
    "save_session",
    "save_summary",
]
