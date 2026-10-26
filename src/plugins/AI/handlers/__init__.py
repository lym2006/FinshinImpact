# src/plugins/AI/handlers/__init__.py
"""AI 路由门面

- 交出全部业务路由的有序清单
"""

from core.domain import PluginRoute

from . import _ai_chat, _history

__all__ = ["get_routes"]


def get_routes() -> tuple[PluginRoute, ...]:
    """按优先级拼出路由清单

    - 子路由顺序即匹配顺序，对话判定必须最后
    """
    return (*_history.routes, *_ai_chat.routes)
