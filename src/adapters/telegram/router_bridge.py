# src/adapters/telegram/router_bridge.py
"""插件路由清单编译

- 按清单顺序组装平台路由，每次交出全新一只
- 谓词只吃处理上下文，原始事件继续按位置交给处理函数
"""

from collections.abc import Sequence

from aiogram import Router
from aiogram.filters import Filter
from aiogram.types import Message

from finshin_sdk import HandlerContext, MessageRoute
from finshin_sdk.domain import RouteMatcher


class _Predicate(Filter):
    """把路由清单里的谓词包成平台过滤器

    - 拿不到处理上下文时一律不接管
    """

    def __init__(self, predicate: RouteMatcher) -> None:
        self._predicate = predicate

    async def __call__(self, raw: Message, ctx: HandlerContext | None = None) -> bool:
        """判定这条消息归不归该谓词管"""
        if ctx is None:
            return False
        return await self._predicate(ctx)


def build_router(routes: Sequence[MessageRoute]) -> Router:
    """按路由清单装配路由

    - 清单的先后即匹配优先级
    """
    router = Router()
    for route in routes:
        router.message(_Predicate(route.predicate))(route.handler)
    return router
