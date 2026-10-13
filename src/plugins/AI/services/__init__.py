# src/plugins/AI/services/__init__.py
"""AI 服务门面

- 提供对话分发与监控出口
"""

from ._ai_chat import handle_ai_chat
from ._monitor import cleanup_loop

__all__ = [
    # AI 对话处理
    "handle_ai_chat",
    # 核心调度与监控
    "cleanup_loop",
]
