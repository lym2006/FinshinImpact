# src/plugins/AI/core/_chat_context.py
"""会话上下文

- 定义全局会话状态与任务队列
- 实现会话守卫装饰器
"""

import asyncio
import functools
import time
from collections.abc import Awaitable, Callable
from typing import ParamSpec, TypeVar, cast

from services.context import HandlerContext
from utils import get_logger

from ..config import ai_config
from ._tasks import TaskQueue
from .models import UserSession

_logger = get_logger("Plg.AI.Session")

# 全局状态存储
user_sessions: dict[str, UserSession] = {}
task_queues: dict[str, TaskQueue] = {}
active_tasks: set[asyncio.Task] = set()


# 泛型类型变量（用于装饰器的类型推导）
P = ParamSpec("P")
T = TypeVar("T")


def _create_new_session() -> UserSession:
    """创建并返回一个新的用户会话对象

    - 人设轮按当前配置与磁盘正文现取
    """
    return UserSession(message=list(ai_config.init))


def session_guard(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
    """自动初始化会话与队列"""

    @functools.wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        ctx = cast(HandlerContext, kwargs["ctx"])
        user = ctx.event.principal.key

        # 初始化用户会话
        if user not in user_sessions:
            user_sessions[user] = _create_new_session()
            _logger.debug(f"[Decorator] 已为 {user} 初始化会话")

        # 检查并初始化任务队列
        if user not in task_queues:
            task_queues[user] = TaskQueue()

        # 更新最后活跃时间
        user_sessions[user].last_active = time.time()

        return await func(*args, **kwargs)

    return wrapper
