# src/plugins/AI/services/_ai_chat.py
"""对话分发服务

- 实现入队、状态提示与监控启动
"""

import asyncio

from services.context import HandlerContext
from utils import get_logger

from ..core import active_tasks, session_states, task_queues
from ..state import session_locks
from ..utils import make_session_key
from ._monitor import monitor_loop

_logger = get_logger("Plg.AI")


async def handle_ai_chat(ctx: HandlerContext) -> None:
    """入队消息并启动监控"""
    key = make_session_key(ctx.event.principal)

    state = session_states[key]
    queue = task_queues[key]

    lock = session_locks[key]
    async with lock:
        await queue.add_task(ctx)

        if not state.is_active:
            _logger.debug(f"{key} 监控循环启动")
            state.is_active = True
            monitor_task = asyncio.create_task(monitor_loop(key))
            active_tasks.add(monitor_task)
            monitor_task.add_done_callback(active_tasks.discard)
        else:
            _logger.info(f"容器 {key} 新任务入队，当前长度: {queue.size}")
