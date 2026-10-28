# src/adapters/telegram/_fields.py
"""Telegram 字段归一取值

- 会话作用域、内容种类与发言人显示名按 Telegram 协议取
- 被引用消息无文字时按种类写占位标记，引用块不交空串
- 用户 id 与消息定位三元组是适配层对外的最小形状
"""

from aiogram.enums import ChatType, ContentType
from aiogram.types import Message, User

from core.domain import ChatScope, ContentKind, Platform
from core.domain.ids import ContainerKey, MessageId, UserId
from core.dto import MsgReferenceDTO

_ANONYMOUS_USER = UserId("unknown")  # 匿名代发无 user 段时的占位值

# 被引用消息无文字时的种类占位，引用块禁交空串
_REPLY_KIND_LABELS = {
    ContentKind.PHOTO: "图片",
    ContentKind.DOCUMENT: "文档",
    ContentKind.AUDIO: "音频",
    ContentKind.ANIMATION: "动图",
    ContentKind.VIDEO: "视频",
}
_REPLY_KIND_DEFAULT = "媒体"


def scope_of(chat_type: str) -> ChatScope:
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


def kind_of(content_type: str) -> ContentKind:
    """归一内容类型

    - 词表外的 Telegram 种类一律 UNKNOWN
    - 语音条与音乐文件同归 AUDIO
    """
    match content_type:
        case ContentType.TEXT:
            return ContentKind.TEXT
        case ContentType.PHOTO:
            return ContentKind.PHOTO
        case ContentType.DOCUMENT:
            return ContentKind.DOCUMENT
        case ContentType.AUDIO | ContentType.VOICE:
            return ContentKind.AUDIO
        case ContentType.ANIMATION:
            return ContentKind.ANIMATION
        case ContentType.VIDEO:
            return ContentKind.VIDEO
        case _:
            return ContentKind.UNKNOWN


def display_name(message: Message) -> str:
    """取发言人显示名

    - 频道或匿名管理员代发时取来源群名
    """
    user = message.from_user
    if user is not None:
        return user.full_name or user.first_name or str(user.id)
    if message.sender_chat is not None:
        return message.sender_chat.title or ""
    return ""


def reply_text_of(reply: Message) -> str:
    """取被引用消息的正文

    - 正文与附文都空且种类可辨即交占位标记
    - 被引用的是贴纸等未收录种类按媒体占位
    """
    text = reply.text or reply.caption
    if text:
        return text
    kind = kind_of(reply.content_type)
    if kind == ContentKind.TEXT:
        return ""
    return f"[{_REPLY_KIND_LABELS.get(kind, _REPLY_KIND_DEFAULT)}]"


def user_id_of(user: User | None) -> UserId:
    """取平台原始用户 id

    - 无 user 段按占位值计，与主体键的 user 段同形
    """
    return UserId(str(user.id)) if user is not None else _ANONYMOUS_USER


def sender_id(message: Message) -> UserId:
    """取发言人 id"""
    return user_id_of(message.from_user)


def build_ref(message: Message, container: ContainerKey) -> MsgReferenceDTO:
    """构造消息定位三元组"""
    return MsgReferenceDTO(
        platform=Platform.TELEGRAM,
        container=container,
        message_id=MessageId(str(message.message_id)),
    )
