# src/bundled/grant/__init__.py
"""授权插件门面

- /grant 与 /ungrant：管理命令的授权名单
"""

from finshin_sdk.domain import BasePlugin, MessageRoute

from ._commands import ROUTES


class GrantPlugin(BasePlugin):
    """授权名单的三条命令与分步待输入"""

    def message_routes(self) -> tuple[MessageRoute, ...]:
        """来向消息的路由清单"""
        return ROUTES


__all__ = [
    # 插件契约
    "GrantPlugin",
]
