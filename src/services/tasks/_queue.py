# src/services/tasks/_queue.py
"""热队列

- 按容器分串存待派发任务
- 出队按优先级与到达序取最靠前的一条
"""

import asyncio
from dataclasses import dataclass, replace

from core.domain import TaskKind, TaskPriority
from core.domain.ids import PrincipalKey, SessionKey

from ..context import HandlerContext


@dataclass(frozen=True, slots=True)
class TaskItem:
    """排队中的一条任务

    - sequence 由队列在入队时按容器到达序补齐
    """

    container_key: SessionKey
    principal_key: PrincipalKey
    kind: TaskKind
    priority: TaskPriority
    ctx: HandlerContext
    sequence: int = 0


class HotQueue:
    """容器级优先级队列

    - 同容器多项共用一串，按 (priority, sequence) 定序
    - 串排空即释放该容器的键与到达序计数
    """

    def __init__(self) -> None:
        self._by_container: dict[SessionKey, list[TaskItem]] = {}
        self._arrived: dict[SessionKey, int] = {}
        self._lock = asyncio.Lock()

    async def push(self, item: TaskItem) -> TaskItem:
        """按容器到达序入队，交回补齐序号的那条

        - 序号从 0 起，同一容器单调递增
        """
        async with self._lock:
            sequence = self._arrived.get(item.container_key, 0)
            self._arrived[item.container_key] = sequence + 1
            queued = replace(item, sequence=sequence)
            self._by_container.setdefault(item.container_key, []).append(queued)
            return queued

    async def pop_next(self, container_key: SessionKey) -> TaskItem | None:
        """取出该容器最靠前的一条，空串交回 None"""
        async with self._lock:
            rows = self._by_container.get(container_key)
            if not rows:
                self._release(container_key)
                return None
            nxt = min(rows, key=lambda row: (row.priority, row.sequence))
            rows.remove(nxt)
            if not rows:
                self._release(container_key)
            return nxt

    def size(self, container_key: SessionKey) -> int:
        """该容器当前排队条数"""
        return len(self._by_container.get(container_key, ()))

    async def discard_all(self) -> int:
        """丢掉全部容器的排队项，交回被丢的条数"""
        async with self._lock:
            count = sum(len(rows) for rows in self._by_container.values())
            for container_key in list(self._by_container):
                self._release(container_key)
            return count

    def _release(self, container_key: SessionKey) -> None:
        """抹掉一个容器的两本账

        - 调用方必须持锁
        """
        self._by_container.pop(container_key, None)
        self._arrived.pop(container_key, None)
