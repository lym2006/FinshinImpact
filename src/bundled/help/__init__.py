# src/bundled/help/__init__.py
"""帮助插件门面

- /help：帮助命令路由出口
- 帮助图在引擎开跑前备好，导入本包不碰磁盘
"""

import asyncio

from core.contracts import BundledPlugin
from finshin_sdk.domain import MessageRoute, PlatformTiming, PluginTiming

from ._commands import ROUTES
from ._services import prewarm


async def _prewarm_menu(capability: object) -> None:
    """引擎开跑前把帮助图画好

    - 画图是同步重活，交线程池防卡事件循环
    - 菜单没变时只算一次指纹，几毫秒
    """
    await asyncio.to_thread(prewarm)


class HelpPlugin(BundledPlugin):
    """帮助图与单命令用法出口"""

    def message_routes(self) -> tuple[MessageRoute, ...]:
        """来向消息的路由清单"""
        return ROUTES

    def timings(self) -> tuple[PluginTiming, ...]:
        """引擎开跑前备图"""
        return (PluginTiming(PlatformTiming.BEFORE_ENGINE_RUN, _prewarm_menu),)


__all__ = [
    # 插件契约
    "HelpPlugin",
]
