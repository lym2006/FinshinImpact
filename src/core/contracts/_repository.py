# src/core/contracts/_repository.py
"""仓库契约

- 定义主体、会话、任务、媒体、黑名单的存取接口与事务边界
"""

from abc import ABC, abstractmethod

from ..domain import TaskStatus
from ..domain.ids import PrincipalKey, SessionKey, TaskId
from ..dto import (
    MediaEntryDTO,
    MsgReferenceDTO,
    PrincipalDTO,
    SessionDTO,
    SessionPatchDTO,
    TaskDTO,
    TaskPatchDTO,
    TaskRequestDTO,
)


class PrincipalRepository(ABC):
    """会话主体仓储"""

    @abstractmethod
    async def upsert(self, principal: PrincipalDTO, display_name: str) -> PrincipalDTO:
        """写入或更新主体"""

    @abstractmethod
    async def find_by_key(self, key: PrincipalKey) -> PrincipalDTO | None:
        """按唯一键查询"""

    @abstractmethod
    async def list_stale(self, before: float) -> tuple[PrincipalDTO, ...]:
        """列出失活主体"""


class SessionRepository(ABC):
    """会话仓储"""

    @abstractmethod
    async def load(
        self, session_key: SessionKey, limit: int | None = None
    ) -> SessionDTO:
        """加载会话快照"""

    @abstractmethod
    async def apply_patch(
        self, session_key: SessionKey, patch: SessionPatchDTO
    ) -> SessionDTO:
        """应用会话增量

        - 会话写入的唯一入口
        """

    @abstractmethod
    async def trim_to(self, session_key: SessionKey, keep_count: int) -> int:
        """裁剪会话历史

        - 返回删除条数
        """

    @abstractmethod
    async def touch(self, session_key: SessionKey, at: float) -> None:
        """刷新活跃时间"""


class TaskRepository(ABC):
    """任务仓储

    - 按 task_id 寻址单任务，按主体键筛任务集
    """

    @abstractmethod
    async def insert(self, request: TaskRequestDTO) -> TaskDTO:
        """落库新任务"""

    @abstractmethod
    async def patch(self, task_id: TaskId, patch: TaskPatchDTO) -> TaskDTO | None:
        """更新任务"""

    @abstractmethod
    async def find(self, task_id: TaskId) -> TaskDTO | None:
        """按 ID 查询"""

    @abstractmethod
    async def list_unfinished(self, key: PrincipalKey) -> tuple[TaskDTO, ...]:
        """列出主体未完成任务

        - 重启恢复与 /status 展示共用
        """

    @abstractmethod
    async def list_by_status(self, status: TaskStatus) -> tuple[TaskDTO, ...]:
        """按状态查询

        - 进程启动时恢复 running 中断任务
        """

    @abstractmethod
    async def delete_by_principal(self, key: PrincipalKey) -> int:
        """清除主体全部任务"""


class MediaRepository(ABC):
    """媒体索引仓储"""

    @abstractmethod
    async def register(self, ref: MsgReferenceDTO, entry: MediaEntryDTO) -> None:
        """登记一条媒体索引"""

    @abstractmethod
    async def locate(self, ref: MsgReferenceDTO) -> tuple[MediaEntryDTO, ...]:
        """按三元组定位媒体"""

    @abstractmethod
    async def delete_by_principal(self, key: PrincipalKey) -> int:
        """清除主体全部媒体索引"""


class BlacklistRepository(ABC):
    """黑名单仓储"""

    @abstractmethod
    async def add(self, key: PrincipalKey, reason: str = "") -> bool:
        """加入黑名单

        - 返回是否存在
        """

    @abstractmethod
    async def remove(self, key: PrincipalKey) -> bool:
        """移出黑名单

        - 返回是否存在
        """

    @abstractmethod
    async def contains(self, key: PrincipalKey) -> bool:
        """判定是否命中"""

    @abstractmethod
    async def list_all(self) -> tuple[str, ...]:
        """列出全部条目"""
