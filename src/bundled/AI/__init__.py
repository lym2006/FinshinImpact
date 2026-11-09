# src/bundled/AI/__init__.py
"""AI 插件门面

- 对话与记忆命令入口
- 声明随 Bot 起停的过期记录清理循环与问答动作
- 订阅引擎开跑前、身份变更与配置校验通过三个平台机会
"""

from core.contracts import BundledPlugin
from finshin_sdk.domain import (
    BackgroundLoop,
    MessageRoute,
    PlatformTiming,
    PluginTiming,
    QueuedAction,
)

from .core import purge_on_identity_changed
from .handlers import get_routes
from .services import chat_task_handler, cleanup_loop, report_lost_tasks, wake_cleanup


class AIPlugin(BundledPlugin):
    """对话、记忆命令与它们背后的清理循环"""

    def message_routes(self) -> tuple[MessageRoute, ...]:
        """来向消息的路由清单"""
        return get_routes()

    def background_loops(self) -> tuple[BackgroundLoop, ...]:
        """过期记录清理循环"""
        return (cleanup_loop,)

    def queued_actions(self) -> tuple[QueuedAction, ...]:
        """问答动作"""
        return (chat_task_handler,)

    def timings(self) -> tuple[PluginTiming, ...]:
        """平台机会的订阅清单"""
        return (
            PluginTiming(PlatformTiming.BEFORE_ENGINE_RUN, report_lost_tasks),
            PluginTiming(PlatformTiming.IDENTITY_CHANGED, purge_on_identity_changed),
            PluginTiming(PlatformTiming.CONFIG_VERIFIED, wake_cleanup),
        )


__all__ = [
    # 插件契约
    "AIPlugin",
]
