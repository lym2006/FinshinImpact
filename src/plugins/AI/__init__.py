# src/plugins/AI/__init__.py
"""AI 插件门面

- 对话与记忆命令入口
- 声明随 Bot 起停的过期记录清理协程与问答任务处理
- 订阅引擎开跑前与身份变更两个平台机会
"""

from core.domain import PlatformTiming, PluginSpec, PluginTiming

from .core import purge_on_identity_changed
from .handlers import get_routes
from .services import chat_task_handler, cleanup_loop, report_lost_tasks

# 插件契约
spec = PluginSpec(
    routes=get_routes(),
    backgrounds=(cleanup_loop,),
    task_handlers=(chat_task_handler,),
    timings=(
        PluginTiming(PlatformTiming.BEFORE_ENGINE_RUN, report_lost_tasks),
        PluginTiming(PlatformTiming.IDENTITY_CHANGED, purge_on_identity_changed),
    ),
)

__all__ = [
    # 插件契约
    "spec",
]
