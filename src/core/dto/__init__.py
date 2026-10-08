# src/core/dto/__init__.py
"""数据传输对象门面

- 定义跨层传递的不可变数据快照，隔绝外部平台与内部实现
- 纯数据无逻辑，禁止反向依赖
"""

from ._content import ContentDTO, MediaEntryDTO
from ._identity import MsgReferenceDTO, PrincipalDTO
from ._interaction import InboundEventDTO, OutboundPayloadDTO
from ._session import MessageDTO, SessionDTO, SessionPatchDTO
from ._task import TaskDTO, TaskPatchDTO, TaskRequestDTO

__all__ = [
    # 身份
    "PrincipalDTO",
    "MsgReferenceDTO",
    # 内容
    "ContentDTO",
    "MediaEntryDTO",
    # 交互
    "OutboundPayloadDTO",
    "InboundEventDTO",
    # 会话
    "MessageDTO",
    "SessionDTO",
    "SessionPatchDTO",
    # 任务
    "TaskDTO",
    "TaskRequestDTO",
    "TaskPatchDTO",
]
