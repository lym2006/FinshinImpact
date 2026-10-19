# src/plugins/AI/core/_chat_context.py
"""会话上下文（内部实现）

- 定义全局会话状态与任务队列
- 实现会话守卫装饰器
"""

import asyncio
import functools
import time
from collections.abc import Awaitable, Callable
from typing import ParamSpec, TypeVar, cast

from aiogram.types import Message

from utils import get_logger

from ..config import ai_config
from ..utils import get_name
from ._tasks import TaskQueue
from .models import UserSession

logger = get_logger("Plg.AI.Session")

# ==================== 全局状态存储 ====================

user_sessions: dict[str, UserSession] = {}
task_queues: dict[str, TaskQueue] = {}
active_tasks: set[asyncio.Task] = set()

# ==================== 内部常量与类型定义 ====================

# 泛型类型变量（用于装饰器的类型推导）
P = ParamSpec("P")
T = TypeVar("T")
_DEFAULT_SESSION = {  # 默认会话模板
    "message": list(ai_config.init),
    "md_status": False,
    "is_active": False,
}

# ==================== 会话管理工具 ====================


def create_new_session() -> UserSession:
    """创建并返回一个新的用户会话对象"""
    return UserSession(**_DEFAULT_SESSION)


# ==================== 会话守卫装饰器 ====================


def session_guard(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
    """自动初始化会话与队列"""

    @functools.wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        message = cast(Message, args[0])
        user = get_name(message)

        # 初始化用户会话
        if user not in user_sessions:
            user_sessions[user] = create_new_session()
            logger.debug(f"[Decorator] 已为 {user} 初始化会话")

            # 将系统提示词写入本地文件
            file_path = ai_config.record_dir / f"temp/{user}.md"
            content = ai_config.init[0]["content"]
            log_content = (
                f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}\n\n"
                f"系统：\n{content}\n\n\n\n\n"
            )
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(log_content)

        # 检查并初始化任务队列
        if user not in task_queues:
            task_queues[user] = TaskQueue()

        # 更新最后活跃时间
        user_sessions[user].last_active = time.time()

        return await func(*args, **kwargs)

    return wrapper
