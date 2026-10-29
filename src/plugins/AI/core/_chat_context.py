# src/plugins/AI/core/_chat_context.py
"""会话上下文

- 定义全局会话状态
- 实现会话守卫装饰器
"""

import asyncio
import functools
import time
from collections.abc import Awaitable, Callable
from typing import ParamSpec, TypeVar, cast

from core.domain.ids import SessionKey
from services.context import HandlerContext
from utils import get_logger

from ..utils import make_session_key
from .models import SessionState

_logger = get_logger("Plg.AI.Session")

# 全局状态存储，键为容器级会话键，同群共用一份活跃时间
session_states: dict[SessionKey, SessionState] = {}

# 在跑的压缩协程，停服时统一收掉
active_tasks: set[asyncio.Task] = set()


# 泛型类型变量（用于装饰器的类型推导）
P = ParamSpec("P")
T = TypeVar("T")


def session_guard(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
    """自动初始化会话并记下活跃时间"""

    @functools.wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        ctx = cast(HandlerContext, kwargs["ctx"])
        key = make_session_key(ctx.event.principal)

        # 初始化容器会话
        if key not in session_states:
            session_states[key] = SessionState()
            _logger.debug(f"[Decorator] 已为 {key} 初始化会话")

        # 更新最后活跃时间
        session_states[key].last_active = time.time()

        return await func(*args, **kwargs)

    return wrapper
