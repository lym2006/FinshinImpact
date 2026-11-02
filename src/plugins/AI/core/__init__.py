# src/plugins/AI/core/__init__.py
"""AI 核心门面

- 网络客户端、在跑协程台账与落库出口
"""

from ._chat_context import active_tasks
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
    # 在跑协程台账
    "active_tasks",
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
