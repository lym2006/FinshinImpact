# src/bundled/help/__init__.py
"""帮助插件门面

- /help：帮助命令路由出口
"""

from finshin_sdk.domain import BasePlugin, MessageRoute

from ._commands import ROUTES
from ._services import prewarm

prewarm()  # 引擎启动前重画一次帮助图


class HelpPlugin(BasePlugin):
    """帮助图与单命令用法出口"""

    def message_routes(self) -> tuple[MessageRoute, ...]:
        """来向消息的路由清单"""
        return ROUTES


__all__ = [
    # 插件契约
    "HelpPlugin",
]
