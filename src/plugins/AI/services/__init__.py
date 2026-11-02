# src/plugins/AI/services/__init__.py
"""AI 服务门面

- 对话分发、任务处理、清理循环与停机交代出口
"""

from ._ai_chat import chat_task_handler, handle_ai_chat
from ._cleanup import cleanup_loop
from ._receipt import report_lost_tasks

__all__ = [
    # AI 对话处理
    "chat_task_handler",
    "handle_ai_chat",
    # 核心调度与监控
    "cleanup_loop",
    # 停机交代
    "report_lost_tasks",
]
