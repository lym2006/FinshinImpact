# src/core/dto/_session.py
"""会话数据传输对象

- 定义消息会话上下文与状态变更的数据快照
"""

from dataclasses import dataclass

from ..domain import ChatRole, Platform
from ..domain.ids import Container, SessionKey


@dataclass(frozen=True, slots=True)
class MessageDTO:
    """单条会话消息"""

    role: ChatRole
    content: str  # 媒体信息剥离，历史只存文本
    created_at: float = 0.0
    sender_id: str = ""  # 判归属防冒名
    sender_name: str = ""  # 记当时名不回改


@dataclass(frozen=True, slots=True)
class SessionDTO:
    """会话快照

    - 只读投影，禁止原地修改
    """

    platform: Platform
    container: Container
    messages: tuple[MessageDTO, ...] = ()
    summary: str = ""  # 压缩摘要，覆盖旧的
    container_name: str = ""
    is_active: bool = False
    last_active: float = 0.0

    @property
    def session_key(self) -> SessionKey:
        return SessionKey(f"{self.platform}:{self.container}")


@dataclass(frozen=True, slots=True)
class SessionPatchDTO:
    """会话增量

    - 修改会话的唯一入参形态
    - None 表示不修改
    """

    append: tuple[MessageDTO, ...] | None = None
    summary: str | None = None
    reset_to_system: bool = False
