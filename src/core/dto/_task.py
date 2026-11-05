# src/core/dto/_task.py
"""任务数据传输对象

- 定义任务队列的只读视图、创建请求与状态增量
"""

from dataclasses import dataclass

from ..domain import TaskKind, TaskPayload, TaskStatus
from ..domain.ids import KEY_SEP, TaskId
from ._identity import MsgReferenceDTO, PrincipalDTO


@dataclass(frozen=True, slots=True)
class TaskDTO:
    """任务只读视图"""

    principal: PrincipalDTO
    kind: TaskKind
    status: TaskStatus
    source_ref: MsgReferenceDTO  # 任务创建源消息

    payload: TaskPayload = ()

    @property
    def task_id(self) -> TaskId:
        return TaskId(f"{self.principal.key}{KEY_SEP}{self.kind}")


@dataclass(frozen=True, slots=True)
class TaskRequestDTO:
    """任务创建请求"""

    principal: PrincipalDTO
    kind: TaskKind
    source_ref: MsgReferenceDTO

    payload: TaskPayload = ()


@dataclass(frozen=True, slots=True)
class TaskPatchDTO:
    """任务增量

    - 状态推进统一走此
    - None 表示不修改
    """

    status: TaskStatus | None = None
