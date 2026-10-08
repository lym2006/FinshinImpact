# src/core/dto/_interaction.py
"""交互数据传输对象

- 定义外发负载与入站事件
"""

from dataclasses import dataclass

from ..domain import ContentKind
from ._content import ContentDTO
from ._identity import MsgReferenceDTO, PrincipalDTO


@dataclass(frozen=True, slots=True)
class OutboundPayloadDTO:
    """外发负载

    - kind 分派文字与媒体两种形态
    """

    kind: ContentKind
    text: str = ""  # 负载文字时为正文，媒体时为附言
    local_path: str = ""  # 仅媒体种类使用
    file_name: str = ""  # 对外展示文件名，缺省取 local_path 末段


@dataclass(frozen=True, slots=True)
class InboundEventDTO:
    """入站事件

    - 中间件与业务层的唯一事件输入
    """

    ref: MsgReferenceDTO
    principal: PrincipalDTO
    content: ContentDTO

    is_command: bool = False
    command_name: str = ""
    command_args: tuple[str, ...] = ()
    reply_ref: MsgReferenceDTO | None = None
    is_mention_bot: bool = False
    created_at: float = 0.0
