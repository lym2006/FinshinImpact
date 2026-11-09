# src/services/tasks/_service.py
"""任务排队与调度

- 同容器排一串逐条派发，跨容器共用一把并发闸
"""

import asyncio
from collections.abc import Callable, Iterable

from finshin_sdk.domain import TaskHandler, TaskRun
from finshin_sdk.domain.ids import SessionKey

from ._ledger import TaskLedger
from ._queue import HotQueue, TaskItem

# 同时开跑的容器数上限，受 AI 服务商 QPS 与本机连接数约束
_MAX_CONCURRENT = 4

_TaskFault = Callable[[TaskItem, Exception], None]


class TaskService:
    """容器级任务排队与派发

    - 处理函数按任务类型取，派发只交处理上下文
    - 报错交回装配侧上报，整串不因单项失败而停
    """

    def __init__(
        self,
        handlers: Iterable[TaskHandler],
        *,
        ledger: TaskLedger,
        on_fault: _TaskFault,
        max_concurrency: int = _MAX_CONCURRENT,
    ) -> None:
        self._handlers: dict[str, TaskRun] = {}
        for declared in handlers:
            self._handlers.setdefault(declared.kind, declared.run)
        self._ledger = ledger
        self._on_fault = on_fault
        self._queue = HotQueue()
        self._runners: dict[SessionKey, asyncio.Task[None]] = {}
        self._gate = asyncio.Semaphore(max_concurrency)

        # 入队、取活与退队共用这把记账锁，防队首交接窗口里两头都以为没人
        self._book_lock = asyncio.Lock()

    async def enqueue(self, item: TaskItem) -> None:
        """排入一条任务，该容器无人消费即起消费协程"""
        async with self._book_lock:
            queued = await self._queue.push(item)
            await self._ledger.enqueue(queued)
            runner = self._runners.get(queued.container_key)
            if runner is None or runner.done():
                self._runners[queued.container_key] = asyncio.create_task(
                    self._drain(queued.container_key)
                )

    def size(self, container_key: SessionKey) -> int:
        """该容器当前排队条数"""
        return self._queue.size(container_key)

    async def release(self) -> None:
        """作废全部排队与在途消费协程"""
        async with self._book_lock:
            runners = list(self._runners.values())
            self._runners.clear()

        # 队列项揣着停机前那套引擎的连接句柄，新引擎接着答必撞错
        for runner in runners:
            runner.cancel()
        if runners:
            await asyncio.gather(*runners, return_exceptions=True)
        await self._queue.discard_all()
        self._ledger.reset()

    async def _drain(self, container_key: SessionKey) -> None:
        """逐条消费该容器，队空即退

        - 取消与崩溃都放掉该容器的活跃标记
        """
        try:
            while True:
                async with self._book_lock:
                    item = await self._queue.pop_next(container_key)
                    if item is None:
                        self._retire(container_key)
                        return
                run = self._handlers.get(item.kind)
                if run is None:
                    self._on_fault(item, LookupError(f"没有 {item.kind} 的处理函数"))
                    await self._ledger.settle(item, failed=True)
                    continue
                async with self._gate:
                    await self._ledger.begin(item)
                    failed = False
                    try:
                        await run(item.ctx)
                    except asyncio.CancelledError:
                        raise
                    except Exception as e:
                        self._on_fault(item, e)
                        failed = True
                await self._ledger.settle(item, failed=failed)
        finally:
            async with self._book_lock:
                self._retire(container_key)

    def _retire(self, container_key: SessionKey) -> None:
        """放掉该容器的消费协程记账

        - 调用方必须持锁
        - 只撤自己那一条，不动后来接替的协程
        """
        if self._runners.get(container_key) is asyncio.current_task():
            self._runners.pop(container_key, None)


_service: TaskService | None = None


def configure_task_service(
    handlers: Iterable[TaskHandler], *, ledger: TaskLedger, on_fault: _TaskFault
) -> TaskService:
    """按本次注册交来的处理清单装配服务

    - 重复装配换整套处理清单，旧实例里在跑的协程归上一次收尾管
    """
    global _service
    _service = TaskService(handlers, ledger=ledger, on_fault=on_fault)
    return _service


def get_task_service() -> TaskService:
    """取已装配的服务

    - 未装配即取属装配顺序错
    """
    if _service is None:
        raise RuntimeError("任务服务尚未装配")
    return _service
