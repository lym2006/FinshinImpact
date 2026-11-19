"""AI 路由门面

- 交出全部业务路由的有序清单
"""

from finshin_sdk import MessageRoute

from . import _ai_chat, _history

__all__ = ["get_routes"]


def get_routes() -> tuple[MessageRoute, ...]:
    """按优先级拼出路由清单

    - 子路由按匹配优先级拼成清单，对话判定在最后
    """
    return (*_history.routes, *_ai_chat.routes)
