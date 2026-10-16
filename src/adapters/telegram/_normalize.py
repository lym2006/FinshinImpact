# src/adapters/telegram/_normalize.py
"""入站事件归一

- 把 Telegram 更新转为平台无关事件
- 向下游注入处理上下文
"""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.enums import ChatType, ContentType
from aiogram.types import Message, TelegramObject, Update

from core.contracts import InteractionPort
from core.domain import ChatScope, ContentKind, Platform, make_container
from core.domain.ids import Container, MessageId, UserId
from core.dto import (
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
_ANONYMOUS_USER = "unknown"  # 匿名代发无 user 段时的占位值

_logger = get_logger("Adapter")


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


def _command_parts(text: str) -> tuple[bool, str, tuple[str, ...]]:
    """解析命令名与参数

    - 首段的 @ 后半一律丢弃，分享链接填出的 /cmd@bot 也能命中
    - 不校验被点名的机器人
    - 命令名保留原大小写
    """
    if not text.startswith(_COMMAND_PREFIX):
        return False, "", ()

    tokens = text[1:].split()
    if not tokens:
        return False, "", ()

    head, *args = tokens
    name, _, _ = head.partition("@")
    return True, name, tuple(args)


def normalize_update(update: Update) -> InboundEventDTO | None:
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

    is_command, command_name, command_args = _command_parts(message.text or "")

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
        is_command=is_command,
        command_name=command_name,
        command_args=command_args,
        reply_ref=build_ref(reply, container) if reply is not None else None,
        reply_text=(reply.text or reply.caption or "") if reply is not None else "",
        created_at=message.date.timestamp(),
    )


class NormalizeMiddleware(BaseMiddleware):
    """归一化中间件

    - 归一成功即向 data 写入 ctx 一个键
    """

    def __init__(self, interaction: InteractionPort) -> None:
        super().__init__()
        self._interaction = interaction

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """归一并放行"""
        if isinstance(event, Update) and event.message is not None:
            try:
                inbound = normalize_update(event)
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
