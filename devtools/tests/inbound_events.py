"""入站事件夹具

- 用例按消息记录拼归一事件，字段形状取自接口包，不碰平台协议
- 命令切分是形状桩，语法判据归适配层那侧的用例守
- 作用域与种类的对应表按平台无关的那套值
"""

import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from finshin_sdk.domain import (  # noqa: E402
    ChatScope,
    ContentKind,
    Platform,
    is_flag_name,
    make_container,
)
from finshin_sdk.domain.ids import ChatId, MessageId, UserId  # noqa: E402
from finshin_sdk.dto import (  # noqa: E402
    CommandDTO,
    ContentDTO,
    InboundEventDTO,
    MediaEntryDTO,
    MsgReferenceDTO,
    PrincipalDTO,
)

_DATE = datetime(2026, 10, 16, 12, 0)

_SCOPES = {
    "private": ChatScope.PRIVATE,
    "group": ChatScope.GROUP,
    "supergroup": ChatScope.GROUP,
}
_KINDS = {
    "text": ContentKind.TEXT,
    "photo": ContentKind.PHOTO,
    "document": ContentKind.DOCUMENT,
    "audio": ContentKind.AUDIO,
    "voice": ContentKind.AUDIO,
    "video": ContentKind.VIDEO,
    "animation": ContentKind.ANIMATION,
}

_COMMAND_PREFIX = "/"
_FLAG_PREFIX = "-"
_COMMAND_NAME_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,31}")


@dataclass(frozen=True)
class Chat:
    """用例侧的会话"""

    id: int
    type: str
    title: str = ""


@dataclass(frozen=True)
class User:
    """用例侧的发言人"""

    id: int
    full_name: str = ""
    username: str = ""


@dataclass(frozen=True)
class Msg:
    """用例侧的一条消息"""

    chat: Chat
    id: int = 7
    sender: User | None = None
    text: str = ""
    caption: str = ""
    content_type: str = "text"
    mentions_bot: bool = False
    quoted: "Msg | None" = None
    date: datetime = _DATE


def message(chat: Chat, **fields: object) -> Msg:
    """构造一条用例消息"""
    return Msg(chat=chat, **fields)  # type: ignore[arg-type]


def parse_command(text: str) -> CommandDTO:
    """按 Telegram 的形状切命令头与片段"""
    if not text.startswith(_COMMAND_PREFIX):
        return CommandDTO()

    pieces = text.split()
    head = pieces[0][len(_COMMAND_PREFIX) :]
    if not _COMMAND_NAME_RE.fullmatch(head):
        return CommandDTO(format_error=True)

    for piece in pieces[1:]:
        if piece.startswith(_FLAG_PREFIX) and not is_flag_name(piece):
            return CommandDTO(format_error=True)

    return CommandDTO(matched=True, head=head, pieces=tuple(pieces[1:]))


def _scope(chat: Chat) -> ChatScope:
    return _SCOPES.get(chat.type, ChatScope.UNKNOWN)


_ANONYMOUS_USER = UserId("unknown")  # 匿名代发无 user 段时的占位值


def _user_id(user: User | None) -> UserId:
    return UserId(str(user.id)) if user is not None else _ANONYMOUS_USER


def _name_of(message: Msg) -> str:
    """取发言人显示名，频道代发时退到群名"""
    if message.sender is not None:
        return message.sender.full_name
    return message.chat.title


def _ref(message: Msg, container: str) -> MsgReferenceDTO:
    return MsgReferenceDTO(
        platform=Platform.TELEGRAM,
        container=container,
        message_id=MessageId(str(message.id)),
    )


def _entries(messages: list[Msg], container: str) -> tuple[MediaEntryDTO, ...]:
    """按张交出媒体索引，单条消息即一张"""
    return tuple(
        MediaEntryDTO(
            kind=_KINDS.get(item.content_type, ContentKind.UNKNOWN),
            local_path="",
            slot=slot,
            message_id=MessageId(str(item.id)),
            caption=item.caption,
        )
        for slot, item in enumerate(messages)
    )


def event(message: Msg, *, bot: User | None = None) -> InboundEventDTO:
    """把一条用例消息拼成入站事件

    - 机器人身份只用于判引用归属，缺省即不认
    """
    return _event([message], command=parse_command(message.text), bot=bot)


def album(messages: list[Msg], *, bot: User | None = None) -> InboundEventDTO:
    """把整组相册并成一条入站事件

    - 锚点取最小消息 id 那条，正文取组内首条附文
    """
    ordered = sorted(messages, key=lambda item: item.id)
    return _event(ordered, command=CommandDTO(), bot=bot)


def _event(
    messages: list[Msg], *, command: CommandDTO, bot: User | None
) -> InboundEventDTO:
    """按组内首条消息拼事件外壳"""
    head = messages[0]
    scope = _scope(head.chat)
    user_id = _user_id(head.sender)
    container = make_container(scope, ChatId(str(head.chat.id)), user_id)
    quoted = head.quoted
    reply_id = _user_id(quoted.sender) if quoted is not None else UserId("")
    text = head.text or next((item.caption for item in messages if item.caption), "")
    media = () if head.content_type == "text" else _entries(messages, container)
    return InboundEventDTO(
        ref=_ref(head, container),
        principal=PrincipalDTO(
            platform=Platform.TELEGRAM, container=container, user=user_id
        ),
        content=ContentDTO(text=text, media=media),
        scope=scope,
        container_name=head.chat.title,
        display_name=_name_of(head),
        command=command,
        reply_ref=_ref(quoted, container) if quoted is not None else None,
        reply_text=(quoted.text or quoted.caption) if quoted is not None else "",
        reply_sender_id=reply_id,
        reply_sender_name=quoted.sender.full_name if quoted is not None else "",
        reply_to_bot=bot is not None and reply_id == UserId(str(bot.id)),
        reply_kind=_KINDS.get(quoted.content_type, ContentKind.UNKNOWN)
        if quoted is not None
        else ContentKind.TEXT,
        is_mention_bot=head.mentions_bot,
        created_at=head.date.timestamp(),
    )
