# src/adapters/telegram/_normalize.py
"""入站事件归一

- 把 Telegram 更新转为平台无关事件
- 命令切分、点名与引用归属按 Telegram 协议判定
- 向下游注入处理上下文
"""

import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from aiogram import BaseMiddleware, Bot
from aiogram.enums import ChatType, ContentType, MessageEntityType
from aiogram.filters import Command
from aiogram.filters.command import CommandException
from aiogram.types import Message, TelegramObject, Update

from core.contracts import InteractionPort
from core.domain import ChatScope, ContentKind, Platform, make_container
from core.domain.ids import Container, MessageId, UserId
from core.dto import (
    CommandDTO,
    ContentDTO,
    InboundEventDTO,
    MediaEntryDTO,
    MsgReferenceDTO,
    PrincipalDTO,
)
from services import HandlerContext
from utils import get_logger

# 协议串
_COMMAND_PREFIX = "/"
_BOT_PREFIX = "@"
_ANONYMOUS_USER = "unknown"  # 匿名代发无 user 段时的占位值

# Telegram 侧命令名与机器人用户名的字符集
_COMMAND_NAME_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,31}")
_BOT_USERNAME_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]{4,31}")

_logger = get_logger("Adapter")


@dataclass(frozen=True, slots=True)
class BotIdentity:
    """本机器人标识

    - mention 与引用归属的比对基准
    """

    user_id: str = ""
    username: str = ""


_UNKNOWN_IDENTITY = BotIdentity()


def _scope_of(chat_type: str) -> ChatScope:
    """归一会话作用域

    - 频道一律归 UNKNOWN
    """
    match chat_type:
        case ChatType.PRIVATE:
            return ChatScope.PRIVATE
        case ChatType.GROUP | ChatType.SUPERGROUP:
            return ChatScope.GROUP
        case _:
            return ChatScope.UNKNOWN


def _kind_of(content_type: str) -> ContentKind:
    """归一内容类型

    - 词表外的 Telegram 种类一律 UNKNOWN
    """
    match content_type:
        case ContentType.TEXT:
            return ContentKind.TEXT
        case ContentType.PHOTO:
            return ContentKind.PHOTO
        case ContentType.DOCUMENT:
            return ContentKind.DOCUMENT
        case ContentType.AUDIO:
            return ContentKind.AUDIO
        case ContentType.VOICE:
            return ContentKind.VOICE
        case ContentType.ANIMATION:
            return ContentKind.ANIMATION
        case ContentType.VIDEO:
            return ContentKind.VIDEO
        case _:
            return ContentKind.UNKNOWN


def _display_name(message: Message) -> str:
    """取发言人显示名

    - 频道或匿名管理员代发时取来源群名
    """
    user = message.from_user
    if user is not None:
        return user.full_name or user.first_name or str(user.id)
    if message.sender_chat is not None:
        return message.sender_chat.title or ""
    return ""


def build_ref(message: Message, container: Container) -> MsgReferenceDTO:
    """构造消息定位三元组"""
    return MsgReferenceDTO(
        platform=Platform.TELEGRAM,
        container=container,
        message_id=MessageId(str(message.message_id)),
    )


def _parse_command(text: str) -> CommandDTO:
    """解析命令形态

    - 首个空格之后一律算参数
    - 命令名与被 @ 的用户名按 Telegram 字符集校验
    - 校验不过判格式错误
    - 命令名保留原大小写
    """
    if not text.startswith(_COMMAND_PREFIX):
        return CommandDTO()

    try:
        raw = Command.extract_command(text)  # 与 aiogram 命令过滤器同口径
    except CommandException:
        return CommandDTO(format_error=True)

    if raw.prefix != _COMMAND_PREFIX or not _COMMAND_NAME_RE.fullmatch(raw.command):
        return CommandDTO(format_error=True)
    if raw.mention and not _BOT_USERNAME_RE.fullmatch(raw.mention):
        return CommandDTO(format_error=True)

    return CommandDTO(
        matched=True,
        name=raw.command,
        args=tuple(raw.args.split()) if raw.args else (),
        mention=raw.mention or "",
    )


def _mentions_bot(message: Message, identity: BotIdentity) -> bool:
    """判定正文是否点名本机器人

    - @ 用户名走 mention 实体，无用户名的点名走 text_mention 实体
    - 命令尾的 /cmd@bot 段由命令载体单独承载
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
                    if str(user.id) == identity.user_id:
                        return True
    return False


def _reply_to_bot(reply: Message | None, identity: BotIdentity) -> bool:
    """判定被引用消息是否本机器人发出"""
    if reply is None or reply.from_user is None or not identity.user_id:
        return False
    return str(reply.from_user.id) == identity.user_id


def normalize_update(
    update: Update, identity: BotIdentity = _UNKNOWN_IDENTITY
) -> InboundEventDTO | None:
    """归一一条更新

    - 非消息更新返回 None
    """
    message = update.message
    if message is None:
        return None

    scope = _scope_of(message.chat.type)
    user = message.from_user
    user_id = str(user.id) if user is not None else _ANONYMOUS_USER
    container = make_container(scope, str(message.chat.id), user_id)
    reply = message.reply_to_message
    kind = _kind_of(message.content_type)

    # 媒体不下载，条目只报种类
    media = ()
    if kind is not ContentKind.TEXT:
        media = (MediaEntryDTO(kind=kind, local_path=""),)

    command = _parse_command(message.text or "")

    return InboundEventDTO(
        ref=build_ref(message, container),
        principal=PrincipalDTO(
            platform=Platform.TELEGRAM,
            container=container,
            user=UserId(user_id),
        ),
        content=ContentDTO(
            text=message.text or message.caption or "",
            media=media,
        ),
        scope=scope,
        container_name=message.chat.title or message.chat.first_name or "",
        display_name=_display_name(message),
        command=command,
        reply_ref=build_ref(reply, container) if reply is not None else None,
        reply_text=(reply.text or reply.caption or "") if reply is not None else "",
        reply_to_bot=_reply_to_bot(reply, identity),
        is_mention_bot=_mentions_bot(message, identity),
        created_at=message.date.timestamp(),
    )


class NormalizeMiddleware(BaseMiddleware):
    """归一化中间件

    - 归一成功即向 data 写入 ctx 一个键
    """

    def __init__(self, interaction: InteractionPort, bot: Bot) -> None:
        super().__init__()
        self._interaction = interaction
        self._bot = bot

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """归一并放行"""
        if isinstance(event, Update) and event.message is not None:
            try:
                me = await self._bot.me()
                inbound = normalize_update(
                    event,
                    BotIdentity(user_id=str(me.id), username=me.username or ""),
                )
            except Exception as e:
                # 单条畸形更新只记日志，不能中断事件流
                _logger.send_error("事件归一失败", e)
                inbound = None
            if inbound is not None:
                data["ctx"] = HandlerContext(
                    event=inbound,
                    interaction=self._interaction,
                )

        return await handler(event, data)
