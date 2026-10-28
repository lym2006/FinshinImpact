# src/adapters/telegram/_event.py
"""入站事件映射

- 把 Telegram 消息与相册转为平台无关事件
- 命令切分、点名与引用归属按 Telegram 协议判定
- 作用域、种类与显示名的取值归在同目录 _fields 里，这里只组装事件
- 只认单条消息与整组两种来源，缓冲与放行不归这里
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass

from aiogram.enums import MessageEntityType
from aiogram.types import Message, Update

from core.domain import ContentKind, Platform, make_container
from core.domain.ids import ChatId, MessageId, UserId
from core.dto import (
    CommandDTO,
    ContentDTO,
    InboundEventDTO,
    MediaEntryDTO,
    PrincipalDTO,
)

from ._fields import (
    build_ref,
    display_name,
    kind_of,
    reply_text_of,
    scope_of,
    sender_id,
    user_id_of,
)

# 协议串
_COMMAND_PREFIX = "/"
_BOT_PREFIX = "@"
_FLAG_PREFIX = "-"

# Telegram 侧命令名与 flag 的形状
_COMMAND_NAME_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,31}")
_FLAG_RE = re.compile(r"-[A-Za-z][A-Za-z0-9_-]*")


@dataclass(frozen=True, slots=True)
class BotIdentity:
    """本机器人标识

    - mention 与引用归属的比对基准
    """

    user_id: UserId = UserId("")
    username: str = ""


_UNKNOWN_IDENTITY = BotIdentity()


def _parse_command(text: str) -> CommandDTO:
    """解析命令三段

    - 首个空格前的片段算命令头，须写成 /命令名
    - 命令名按 Telegram 字符集校验，带 @ 段判非法
    - 空格之后 `-` 开头的片段算 flag，其余落 args
    - flag 只校验形状，支持哪些开关由插件清单声明
    - 命令名保留原大小写
    """
    if not text.startswith(_COMMAND_PREFIX):
        return CommandDTO()

    pieces = text.split()
    head = pieces[0][len(_COMMAND_PREFIX) :]
    if not _COMMAND_NAME_RE.fullmatch(head):
        return CommandDTO(format_error=True)

    flags: list[str] = []
    args: list[str] = []
    for piece in pieces[1:]:
        if piece.startswith(_FLAG_PREFIX):
            if not _FLAG_RE.fullmatch(piece):
                return CommandDTO(format_error=True)
            flags.append(piece)
            continue
        args.append(piece)

    return CommandDTO(
        matched=True,
        head=head,
        flags=tuple(flags),
        args=tuple(args),
    )


def _mentions_bot(message: Message, identity: BotIdentity) -> bool:
    """判定正文是否点名本机器人

    - @ 用户名走 mention 实体，无用户名的点名走 text_mention 实体
    """
    if not message.entities or not (identity.username or identity.user_id):
        return False

    for entity in message.entities:
        match entity.type:
            case MessageEntityType.MENTION:
                named = entity.extract_from(message.text or "")
                target = _BOT_PREFIX + identity.username
                if identity.username and named.casefold() == target.casefold():
                    return True
            case MessageEntityType.TEXT_MENTION:
                user = entity.user
                if user is not None and identity.user_id:
                    if user_id_of(user) == identity.user_id:
                        return True
    return False


def _reply_to_bot(reply: Message | None, identity: BotIdentity) -> bool:
    """判定被引用消息是否本机器人发出"""
    if reply is None or reply.from_user is None or not identity.user_id:
        return False
    return user_id_of(reply.from_user) == identity.user_id


def _entry_of(message: Message, kind: ContentKind, slot: int = 0) -> MediaEntryDTO:
    """构造一张媒体的索引条目

    - 媒体不下载，条目只报种类、消息 id 与该张附文
    """
    return MediaEntryDTO(
        kind=kind,
        local_path="",
        slot=slot,
        message_id=MessageId(str(message.message_id)),
        caption=message.caption or "",
    )


def _event_of(
    message: Message,
    identity: BotIdentity,
    *,
    text: str,
    command: CommandDTO,
    media: tuple[MediaEntryDTO, ...],
) -> InboundEventDTO:
    """按一条消息组装归一事件外壳

    - 定位锚点与发言人显示名都取这条消息
    - 命令片段由调用方给定，媒体附文不参与解析
    """
    scope = scope_of(message.chat.type)
    user_id = sender_id(message)
    container = make_container(scope, ChatId(str(message.chat.id)), user_id)
    reply = message.reply_to_message

    return InboundEventDTO(
        ref=build_ref(message, container),
        principal=PrincipalDTO(
            platform=Platform.TELEGRAM,
            container=container,
            user=user_id,
        ),
        content=ContentDTO(text=text, media=media),
        scope=scope,
        container_name=message.chat.title or message.chat.first_name or "",
        display_name=display_name(message),
        command=command,
        reply_ref=build_ref(reply, container) if reply is not None else None,
        reply_text=reply_text_of(reply) if reply is not None else "",
        reply_sender_id=sender_id(reply) if reply is not None else UserId(""),
        reply_sender_name=display_name(reply) if reply is not None else "",
        reply_to_bot=_reply_to_bot(reply, identity),
        is_mention_bot=_mentions_bot(message, identity),
        created_at=message.date.timestamp(),
    )


def normalize_update(
    update: Update, *, identity: BotIdentity = _UNKNOWN_IDENTITY
) -> InboundEventDTO | None:
    """归一一条更新

    - 非消息更新返回 None
    """
    message = update.message
    if message is None:
        return None

    kind = kind_of(message.content_type)
    media = () if kind == ContentKind.TEXT else (_entry_of(message, kind),)

    return _event_of(
        message,
        identity,
        text=message.text or message.caption or "",
        command=_parse_command(message.text or ""),
        media=media,
    )


def normalize_album(
    messages: Sequence[Message], *, identity: BotIdentity = _UNKNOWN_IDENTITY
) -> InboundEventDTO | None:
    """并组相册为一条归一事件

    - 锚点取最小消息 id 的那条，外发引用只能挂一张
    - 正文取组内首条附文，逐张附文留在各自条目里
    """
    if not messages:
        return None

    ordered = sorted(messages, key=lambda item: item.message_id)
    media = tuple(
        _entry_of(item, kind_of(item.content_type), slot=index)
        for index, item in enumerate(ordered)
    )
    caption = next((item.caption or "" for item in ordered if item.caption), "")

    return _event_of(
        ordered[0],
        identity,
        text=caption,
        command=CommandDTO(),
        media=media,
    )
