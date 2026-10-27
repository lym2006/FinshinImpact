# src/utils/middleware.py
"""日志中间件

- 定义访问与异常统一记录管道
"""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from core.domain import ChatScope, ContentKind
from core.dto import ContentDTO, InboundEventDTO
from services.context import HandlerContext

from .logger import get_logger

# 会话作用域与内容种类的中文标签，词表外按未知计
_SCOPE_LABELS = {
    ChatScope.PRIVATE: "私聊",
    ChatScope.GROUP: "群组",
    ChatScope.UNKNOWN: "未知",
}
_KIND_LABELS = {
    ContentKind.TEXT: "文本",
    ContentKind.PHOTO: "图片",
    ContentKind.DOCUMENT: "文档",
    ContentKind.AUDIO: "音频",
    ContentKind.ANIMATION: "动图",
    ContentKind.VIDEO: "视频",
    ContentKind.UNKNOWN: "未知",
}

# 量词，图片按张计其余按条计
_MEASURES = {ContentKind.PHOTO: "张"}
_DEFAULT_MEASURE = "条"

# 预览截断长度与省略号
_PREVIEW_LIMIT = 60
_CAPTION_LIMIT = 30
_TRUNCATED = "..."

# 归一事件缺席时的占位
_LABEL_UNKNOWN = "未知"
_ID_UNKNOWN = "未知"
_NAME_UNKNOWN = "无名氏"
_CHAT_UNKNOWN = "未知聊天"


def _preview(text: str, limit: int) -> str:
    """按上限截断预览"""
    return text if len(text) <= limit else text[:limit] + _TRUNCATED


def _reply_segment(inbound: InboundEventDTO) -> str:
    """被引用消息的发言人与原文"""
    if inbound.reply_ref is None:
        return ""
    sender_id = inbound.reply_sender_id or _ID_UNKNOWN
    sender_name = inbound.reply_sender_name or _NAME_UNKNOWN
    quoted = _preview(inbound.reply_text, _PREVIEW_LIMIT)
    return f"引用 用户{sender_id}<{sender_name}>「{quoted}」"


def _content_segments(content: ContentDTO) -> list[str]:
    """张数与逐张附文各列一段

    - 张数按媒体条目计，同图的多档分辨率只算一条目
    - 正文取自首条附文，逐张仍按各自 id 单列
    """
    if not content.media:
        text_label = _KIND_LABELS[ContentKind.TEXT]
        preview = _preview(content.text, _PREVIEW_LIMIT)
        return [f"[长度：{len(content.text)}] {text_label}：{preview}"]

    counts: dict[ContentKind, int] = {}
    for entry in content.media:
        counts[entry.kind] = counts.get(entry.kind, 0) + 1

    segments = [
        f"{_KIND_LABELS.get(kind, _LABEL_UNKNOWN)}消息：{total}"
        f"{_MEASURES.get(kind, _DEFAULT_MEASURE)}"
        for kind, total in counts.items()
    ]
    segments.extend(
        f"附文[{entry.message_id}]{_preview(entry.caption, _CAPTION_LIMIT)}"
        for entry in content.media
        if entry.caption
    )
    return segments


class LoggingMiddleware(BaseMiddleware):
    """访问日志中间件

    - 读归一化中间件写入的上下文，整组相册只点一次
    """

    def __init__(self) -> None:
        super().__init__()

        # 使用专属子 Logger，便于在日志中区分中间件产生的记录
        self._logger = get_logger("Middleware")

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """记录访问并放行"""
        ctx = data.get("ctx")
        if isinstance(ctx, HandlerContext):
            try:
                self._logger.info(self._build_log_entry(ctx.event))
            except Exception as e:
                # 日志构建失败只记自身异常，不影响事件放行
                self._logger.send_error("访问日志构建失败", e)

        return await handler(event, data)

    def _build_log_entry(self, inbound: InboundEventDTO) -> str:
        """构建日志条目

        - 形如：[tg] 群组[g100123]<测试群> | 用户456<张三> 发送 引用 用户123<李四>「在吗」 图片消息：2张
        """
        scope = _SCOPE_LABELS.get(inbound.scope, _LABEL_UNKNOWN)
        chat_name = inbound.container_name or _CHAT_UNKNOWN
        sender_id = inbound.principal.user or _ID_UNKNOWN
        sender_name = inbound.display_name or _NAME_UNKNOWN
        segments = [_reply_segment(inbound), *_content_segments(inbound.content)]
        body = " ".join(segment for segment in segments if segment)

        return (
            f"[{inbound.ref.platform}] {scope}[{inbound.ref.container}]"
            f"<{chat_name}> | 用户{sender_id}<{sender_name}> 发送 {body}"
        )
