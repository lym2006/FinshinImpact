# src/core/contracts/_repository.py
"""仓库契约

- 定义主体、会话、任务、媒体、命令授权的存取接口
"""

from abc import ABC, abstractmethod

from ..domain.ids import PrincipalKey, SessionKey, TaskId, UserId
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
        """应用会话增量"""

    @abstractmethod
    async def delete(self, session_key: SessionKey) -> int:
        """按会话键清除一串会话与消息

        - 键不在库内即零
        - 返回清除条数
        """

    @abstractmethod
    async def delete_all(self) -> None:
        """清除全部会话与消息"""

    @abstractmethod
    async def delete_idle(self, before: float) -> int:
        """清除最后问答时间早于界限的会话

        - 返回清除条数
        """


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

        - /clear 圈定范围与 /status 展示共用
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


class GrantRepository(ABC):
    """命令授权仓储

    - owner 名单在 config，不进本表
    - 键为用户在本平台的 id，库随实例分开
    """

    @abstractmethod
    async def grant(
        self,
        user: UserId,
        granted_by: PrincipalKey,
        expires_at: float | None = None,
    ) -> bool:
        """授予权限

        - 返回是否新增
        - expires_at 为 None 即永久
        """

    @abstractmethod
    async def revoke(self, user: UserId) -> bool:
        """撤销权限

        - 返回是否存在
        """

    @abstractmethod
    async def list_active(self) -> tuple[UserId, ...]:
        """列出未到期的授权

        - 按授权先后升序
        """

    @abstractmethod
    async def contains(self, user: UserId) -> bool:
        """判定是否命中"""
