# src/plugins/AI/core/_tasks.py
"""任务队列

- 实现异步任务队列管理
"""

import asyncio
from collections import deque

from services.context import HandlerContext


class TaskQueue:
    """管理消息任务的队列"""

    def __init__(self) -> None:
        self._queue: deque[HandlerContext] = deque()
        self._lock = asyncio.Lock()

    async def add_task(self, task: HandlerContext) -> None:
        """向队列尾部添加一个任务"""
        async with self._lock:
            self._queue.append(task)

    async def peek_front(self) -> HandlerContext | None:
        """查看队首任务但不将其移出队列"""
        async with self._lock:
            return self._queue[0] if self._queue else None

    async def pop_front(self) -> HandlerContext | None:
        """从队首弹出一个任务"""
        async with self._lock:
            return self._queue.popleft() if self._queue else None

    @property
    def size(self) -> int:
        """获取当前队列中的任务数量"""
        return len(self._queue)
