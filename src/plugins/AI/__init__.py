# src/plugins/AI/__init__.py
"""AI 插件门面

- 提供对话与记忆命令入口
- 声明随 Bot 起停的过期记录清理协程、会话记录清理入口、问答任务处理与停机交代入口
"""

from core.domain import PluginSpec

from .core import purge_history
from .handlers import get_routes
from .services import chat_task_handler, cleanup_loop, report_lost_tasks

# 插件契约
spec = PluginSpec(
    routes=get_routes(),
    backgrounds=(cleanup_loop,),
    history_reset=purge_history,
    task_handlers=(chat_task_handler,),
    startups=(report_lost_tasks,),
)

__all__ = [
    # 插件契约
    "spec",
]
