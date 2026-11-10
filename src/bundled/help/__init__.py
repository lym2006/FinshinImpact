# src/bundled/help/__init__.py
"""帮助插件门面

- /help：帮助命令路由出口
- 帮助图在引擎开跑前备好
"""

import asyncio

from finshin_sdk.domain import (
    BasePlugin,
    MessageRoute,
    MomentSubscription,
    PlatformMoment,
)

from ._commands import ROUTES
from ._services import prewarm


async def _prewarm_menu(capability: object) -> None:
    """引擎开跑前把帮助图画好"""
    # 画图是同步重活，交线程池防卡事件循环
    await asyncio.to_thread(prewarm)


class HelpPlugin(BasePlugin):
    """帮助图与单命令用法出口"""

    def message_routes(self) -> tuple[MessageRoute, ...]:
        """来向消息的路由清单"""
        return ROUTES

    def platform_moments(self) -> tuple[MomentSubscription, ...]:
        """引擎开跑前备图"""
        return (MomentSubscription(PlatformMoment.BEFORE_ENGINE_RUN, _prewarm_menu),)


__all__ = [
    # 插件契约
    "HelpPlugin",
]
