# src/finshin_sdk/dto/__init__.py
"""数据传输对象门面

- 定义跨层传递的不可变数据快照
"""

from ._adapter import AdapterManifestDTO
from ._content import ContentDTO, MediaEntryDTO
from ._identity import MsgReferenceDTO, PrincipalDTO
from ._interaction import CommandDTO, InboundEventDTO, OutboundPayloadDTO
from ._plugin import HelpCommandDTO, HelpFlagDTO, HelpSectionDTO, PluginManifestDTO
from ._session import MessageDTO, SessionDTO, SessionPatchDTO
from ._task import TaskDTO, TaskPatchDTO, TaskRequestDTO

__all__ = [
    # 身份
    "PrincipalDTO",
    "MsgReferenceDTO",
    # 内容
    "ContentDTO",
    "MediaEntryDTO",
    # 插件
    "HelpCommandDTO",
    "HelpFlagDTO",
    "HelpSectionDTO",
    "PluginManifestDTO",
    # 适配器
    "AdapterManifestDTO",
    # 交互
    "OutboundPayloadDTO",
    "InboundEventDTO",
    "CommandDTO",
    # 会话
    "MessageDTO",
    "SessionDTO",
    "SessionPatchDTO",
    # 任务
    "TaskDTO",
    "TaskRequestDTO",
    "TaskPatchDTO",
]
