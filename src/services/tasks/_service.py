# src/services/tasks/_service.py
"""任务排队与调度

- 同容器排一串逐条派发，跨容器共用一把并发闸
- 每容器一条消费协程，退出即放掉该容器的活跃标记
"""

import asyncio
from collections.abc import Awaitable, Callable, Mapping

from core.domain import TaskKind
from core.domain.ids import SessionKey

from ..context import HandlerContext
from ._queue import HotQueue, TaskItem

# 同时开跑的容器数上限，受 AI 服务商 QPS 与本机连接数约束
_MAX_CONCURRENT = 4

_TaskRun = Callable[[HandlerContext], Awaitable[None]]
_TaskFault = Callable[[TaskItem, Exception], None]


class TaskService:
    """容器级任务排队与派发

    - handler 按任务类型取，派发只交处理上下文
    - 报错交回装配侧上报，整串不因单项失败而停
    """

    def __init__(
        self,
        handlers: Mapping[TaskKind, _TaskRun],
        *,
        on_fault: _TaskFault,
        max_concurrency: int = _MAX_CONCURRENT,
    ) -> None:
        self._handlers = handlers
        self._on_fault = on_fault
        self._queue = HotQueue()
        self._runners: dict[SessionKey, asyncio.Task[None]] = {}
        self._gate = asyncio.Semaphore(max_concurrency)

    async def enqueue(self, item: TaskItem) -> None:
        """排入一条任务，该容器无人消费即起消费协程"""
        queued = await self._queue.push(item)
        runner = self._runners.get(queued.container_key)
        if runner is None or runner.done():
            self._runners[queued.container_key] = asyncio.create_task(
                self._drain(queued.container_key)
            )

    async def _drain(self, container_key: SessionKey) -> None:
        """逐条消费该容器，队空即退

        - 取消与崩溃都放掉该容器的活跃标记
        """
        try:
            while True:
                item = await self._queue.pop_next(container_key)
                if item is None:
                    return
                run = self._handlers.get(item.kind)
                if run is None:
                    self._on_fault(item, LookupError(f"没有 {item.kind} 的处理函数"))
                    continue
                async with self._gate:
                    try:
                        await run(item.ctx)
                    except asyncio.CancelledError:
                        raise
                    except Exception as e:
                        self._on_fault(item, e)
        finally:
            if self._runners.get(container_key) is asyncio.current_task():
                self._runners.pop(container_key, None)
