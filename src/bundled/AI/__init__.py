"""AI 插件门面

- 对话与记忆命令入口
- 声明随 Bot 起停的过期记录清理循环与问答动作
- 订阅引擎开跑前、身份变更与配置校验通过三个平台机会
- 交出本插件认领的来源标题与模型、主人两段的配置字段表
"""

from finshin_sdk import (
    BackgroundLoop,
    BasePlugin,
    MessageRoute,
    MomentSubscription,
    PlatformMoment,
    QueuedAction,
    SourceDeclaration,
)

from .config import CONFIG_SOURCE
from .core import purge_on_identity_changed
from .handlers import get_routes
from .services import chat_task_handler, cleanup_loop, report_lost_tasks, wake_cleanup


class AIPlugin(BasePlugin):
    """对话与记忆命令及清理循环"""

    def message_routes(self) -> tuple[MessageRoute, ...]:
        """来向消息的路由清单"""
        return get_routes()

    def background_loops(self) -> tuple[BackgroundLoop, ...]:
        """过期记录清理循环"""
        return (cleanup_loop,)

    def queued_actions(self) -> tuple[QueuedAction, ...]:
        """问答动作"""
        return (chat_task_handler,)

    def platform_moments(self) -> tuple[MomentSubscription, ...]:
        """平台机会的订阅清单"""
        return (
            MomentSubscription(PlatformMoment.BEFORE_ENGINE_RUN, report_lost_tasks),
            MomentSubscription(
                PlatformMoment.IDENTITY_CHANGED, purge_on_identity_changed
            ),
            MomentSubscription(PlatformMoment.CONFIG_VERIFIED, wake_cleanup),
        )

    def source_declaration(self) -> SourceDeclaration:
        """来源标题与模型、主人两段的字段表"""
        return CONFIG_SOURCE


__all__ = [
    # 插件契约
    "AIPlugin",
]
