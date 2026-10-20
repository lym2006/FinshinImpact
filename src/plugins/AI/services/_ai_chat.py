# src/plugins/AI/services/_ai_chat.py
"""对话分发服务

- 实现入队、状态提示与监控启动
"""

import asyncio

from services.context import HandlerContext
from utils import get_logger

from ..core import active_tasks, task_queues, user_sessions
from ..state import user_locks
from ._monitor import monitor_loop

_logger = get_logger("Plg.AI")


async def handle_ai_chat(ctx: HandlerContext) -> None:
    """入队消息并启动监控"""
    user = ctx.event.principal.key

    session = user_sessions[user]
    queue = task_queues[user]

    lock = user_locks[user]
    async with lock:
        await queue.add_task(ctx)

        if not session.is_active:
            _logger.debug(f"{user} 监控循环启动")
            session.is_active = True
            monitor_task = asyncio.create_task(monitor_loop(user))
            active_tasks.add(monitor_task)
            monitor_task.add_done_callback(active_tasks.discard)
        else:
            _logger.info(f"用户 {user} 新任务入队，当前长度: {queue.size}")
