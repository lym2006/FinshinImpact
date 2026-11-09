# src/services/tasks/_ledger.py
"""任务状态账

- 同一主体的一串问答共记库里一行，入队、开答、落定三处推进
- 记不进只上报，派发照走
"""

from collections.abc import Callable
from pathlib import Path

from data import Repositories, build_repositories, get_connection
from finshin_sdk.domain import TaskStatus
from finshin_sdk.domain.ids import KEY_SEP, PrincipalKey, TaskId
from finshin_sdk.dto import TaskPatchDTO, TaskRequestDTO

from ._queue import TaskItem

_LedgerFault = Callable[[TaskItem, Exception], None]


class TaskLedger:
    """主体级粗账

    - 库里看不出这一串欠几条，中间某条单独失败只进上报
    """

    def __init__(self, db_path: Path, *, on_fault: _LedgerFault) -> None:
        self._db_path = db_path
        self._on_fault = on_fault
        self._repos: Repositories | None = None

        # 在途计数归零即代表整串落定，开过答的主体整串只推到在跑一次
        self._inflight: dict[PrincipalKey, int] = {}
        self._began: set[PrincipalKey] = set()

    async def enqueue(self, item: TaskItem) -> None:
        """记入队

        - 该主体这一串的头一条才落库，后续只加在途计数
        - 主体行随任务行一起写，外键才有落点
        """
        key = item.principal_key
        if self._inflight.get(key, 0) > 0:
            self._inflight[key] += 1
            return
        self._inflight[key] = 1

        principal = item.ctx.event.principal
        try:
            repos = await self._book()
            await repos.principal.upsert(principal, item.ctx.event.display_name)
            await repos.task.insert(
                TaskRequestDTO(
                    principal=principal,
                    kind=item.kind,
                    source_ref=item.ctx.event.ref,
                )
            )
        except Exception as e:
            self._on_fault(item, e)

    async def begin(self, item: TaskItem) -> None:
        """记开答

        - 同一串只推到在跑一次
        """
        key = item.principal_key
        if key in self._began:
            return
        self._began.add(key)
        await self._patch(item, TaskPatchDTO(status=TaskStatus.RUNNING))

    async def settle(self, item: TaskItem, *, failed: bool) -> None:
        """记落定

        - 在途计数归零才写终态
        - 没开过答就落定即没答上，按失败记
        """
        key = item.principal_key
        left = self._inflight.get(key, 0) - 1
        if left > 0:
            self._inflight[key] = left
            return
        self._inflight.pop(key, None)
        began = key in self._began
        self._began.discard(key)
        status = TaskStatus.SUCCEEDED if began and not failed else TaskStatus.FAILED
        await self._patch(item, TaskPatchDTO(status=status))

    def reset(self) -> None:
        """抹掉内存里的两本账

        - 库里那行原样留着，欠下的问答由下次启动交代
        """
        self._inflight.clear()
        self._began.clear()

    async def _book(self) -> Repositories:
        """取出仓储集合"""
        # 首次用时按当前事件循环装配，之后每次走同一条连接
        if self._repos is None:
            self._repos = build_repositories(await get_connection(self._db_path))
        return self._repos

    async def _patch(self, item: TaskItem, patch: TaskPatchDTO) -> None:
        """推进状态，报错与查无此行一并上报"""
        task_id = TaskId(f"{item.principal_key}{KEY_SEP}{item.kind}")
        try:
            repos = await self._book()
            await repos.task.patch(task_id, patch)
        except Exception as e:
            self._on_fault(item, e)
