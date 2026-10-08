# src/core/dto/_task.py
"""任务数据传输对象

- 定义任务队列的只读视图、创建请求与状态增量
"""

from dataclasses import dataclass

from ..domain import TaskKind, TaskPayload, TaskPriority, TaskStatus
from ..domain.ids import TaskId
from ._content import ContentDTO
from ._identity import MsgReferenceDTO, PrincipalDTO


@dataclass(frozen=True, slots=True)
class TaskDTO:
    """任务只读视图"""

    principal: PrincipalDTO
    kind: TaskKind
    status: TaskStatus
    priority: TaskPriority
    source_ref: MsgReferenceDTO  # 任务创建源消息

    payload: TaskPayload = ()
    created_at: float = 0.0
    started_at: float | None = None
    finished_at: float | None = None
    error_text: str = ""

    @property
    def task_id(self) -> TaskId:
        return TaskId(f"{self.principal.key}:{self.kind}")


@dataclass(frozen=True, slots=True)
class TaskRequestDTO:
    """任务创建请求

    - enqueue 的唯一入参
    """

    principal: PrincipalDTO
    kind: TaskKind
    source_ref: MsgReferenceDTO

    priority: TaskPriority = TaskPriority.NORMAL
    dedupe_key: str = ""  # 防重复提交
    content: ContentDTO | None = None
    payload: TaskPayload = ()


@dataclass(frozen=True, slots=True)
class TaskPatchDTO:
    """任务增量

    - 状态推进统一走此
    - None 表示不修改
    """

    status: TaskStatus | None = None
    error_text: str | None = None
