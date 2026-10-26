# src/adapters/telegram/router_bridge.py
"""插件路由清单编译

- 按清单顺序组装 aiogram 的 Router，每次交出全新一只
- 谓词只吃处理上下文，原始事件继续按位置交给处理函数
"""

from aiogram import Router
from aiogram.filters import Filter
from aiogram.types import Message

from core.domain import PluginPredicate, PluginSpec
from services.context import HandlerContext


class _Predicate(Filter):
    """把清单里的谓词包成 aiogram 过滤器

    - 拿不到处理上下文时一律不接管
    """

    def __init__(self, predicate: PluginPredicate) -> None:
        self._predicate = predicate

    async def __call__(self, raw: Message, ctx: HandlerContext | None = None) -> bool:
        """判定这条消息归不归该谓词管"""
        if ctx is None:
            return False
        return await self._predicate(ctx)


def build_router(spec: PluginSpec) -> Router:
    """按清单装配路由

    - routes 的顺序即匹配优先级
    """
    router = Router()
    for route in spec.routes:
        router.message(_Predicate(route.predicate))(route.handler)
    return router
