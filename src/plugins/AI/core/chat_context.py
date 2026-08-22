# src/plugins/AI/core/session.py
"""
AI 核心会话管理

提供：
- 全局会话状态
- 全局任务队列
- 会话守卫装饰器：自动处理初始化与本地日志记录
"""

import asyncio
import copy
import functools
import logging
import time
from collections.abc import Awaitable, Callable
from typing import ParamSpec, TypeVar, cast

from aiogram.types import Message

from .config import INIT, RECORD_DIR
from .models import UserSession
from .task import TaskQueue
from .utils import get_name

logger_session = logging.getLogger("Bot.Plugins.AI.Session")

# ==================== 1. 全局状态存储 ====================
user_sessions: dict[str, UserSession] = {}
task_queues: dict[str, TaskQueue] = {}
active_tasks: set[asyncio.Task] = set()

# 默认会话模板（深拷贝防止污染）
_DEFAULT_SESSION = {
    "message": copy.deepcopy(INIT),
    "md_status": False,
    "is_active": False,
}

# 泛型类型变量（用于装饰器的类型推导）
P = ParamSpec("P")
T = TypeVar("T")


# ==================== 2. 会话管理工具 ====================
def create_new_session() -> UserSession:
    """创建并返回一个新的用户会话对象"""
    return UserSession(**_DEFAULT_SESSION)


# ==================== 3. 会话守卫装饰器 ====================
def session_guard(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
    """自动初始化用户会话和任务队列，并记录到本地文件"""

    @functools.wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        message = cast(Message, args[0])
        user = get_name(message)

        # 1. 初始化用户会话
        if user not in user_sessions:
            user_sessions[user] = create_new_session()
            logger_session.info(f"🆕 [Decorator] 已为 {user} 初始化会话")

            # 将系统提示词写入本地文件
            file_path = RECORD_DIR / f"temp/{user}.md"
            content = INIT[0]["content"]
            log_content = (
                f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}\n\n"
                f"系统：\n{content}\n\n\n\n\n"
            )
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(log_content)

        # 2. 检查并初始化任务队列
        if user not in task_queues:
            task_queues[user] = TaskQueue()

        # 3. 更新最后活跃时间
        user_sessions[user].last_active = time.time()

        return await func(*args, **kwargs)

    return wrapper
