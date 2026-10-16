# src/core/dto/_interaction.py
"""交互数据传输对象

- 定义外发负载与入站事件
"""

from dataclasses import dataclass, field

from ..domain import ChatScope, ContentKind
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
class CommandDTO:
    """命令片段

    - matched 为真时 name 与 args 才有效
    - format_error 标记以命令前缀开头但形态非法的消息
    """

    matched: bool = False
    name: str = ""
    args: tuple[str, ...] = ()
    mention: str = ""  # 命令尾 @ 段，判定是否发给本 bot
    format_error: bool = False


@dataclass(frozen=True, slots=True)
class InboundEventDTO:
    """入站事件"""

    ref: MsgReferenceDTO
    principal: PrincipalDTO
    content: ContentDTO
    scope: ChatScope
    container_name: str = ""
    display_name: str = ""  # 落 MessageDTO.sender_name

    command: CommandDTO = field(default_factory=CommandDTO)
    reply_ref: MsgReferenceDTO | None = None
    reply_text: str = ""  # 只取被引用消息的一层文字
    reply_to_bot: bool = False  # 被引用消息由本 bot 发出
    is_mention_bot: bool = False  # 正文实体点名本 bot
    created_at: float = 0.0
