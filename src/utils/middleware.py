# src/utils/middleware.py
"""日志中间件

- 定义访问与异常统一记录管道
"""

import re
from collections.abc import Awaitable, Callable
from typing import Any

from core.domain import ChatScope, ContentKind
from core.dto import InboundEventDTO
from services.context import HandlerContext

from .logger import get_logger
from .speaker import bot_quote_block, clean_name, quote_block, speaker_mark

# 会话作用域与内容种类的中文标签，词表外按未知计
_SCOPE_LABELS = {
    ChatScope.PRIVATE: "私聊",
    ChatScope.GROUP: "群聊",
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

# 内容槽的计量标签，日志只报体量不抄正文
_TEXT_LABEL = "文本"
_TEXT_UNIT = "字"
_CAPTION_LABEL = "附文"
_COMMAND_LABEL = "命令"
_UNKNOWN = "未知"

# 适配层按种类给的媒体占位标记，形如 [图片]
_KIND_PLACEHOLDER = re.compile(r"\[[^[\]]{1,8}\]")

# 正文里的连续空白折成单空格，一条日志只占一行
_SPACE_RUN = re.compile(r"\s+")


def _quoted_token(text: str) -> str:
    """被引消息的内容槽

    - 适配层按种类给的占位标记原样带过，其余只报字数
    """
    if _KIND_PLACEHOLDER.fullmatch(text):
        return text
    return f"[{_TEXT_LABEL} {len(text)}{_TEXT_UNIT}]"


def _reply_segment(inbound: InboundEventDTO) -> str:
    """被引用消息的标注帧与内容槽

    - 无引用文字即整块省略
    """
    if inbound.reply_ref is None or not inbound.reply_text:
        return ""
    token = _quoted_token(inbound.reply_text)
    if inbound.reply_to_bot:
        return bot_quote_block(token)
    return quote_block(inbound.reply_sender_id, inbound.reply_sender_name, token)


def _head_segment(inbound: InboundEventDTO) -> str:
    """作用域与容器段

    - 私聊的容器段就是发言人，标注帧里已经带全，此处不重复
    """
    scope = _SCOPE_LABELS.get(inbound.scope, _UNKNOWN)
    if inbound.scope != ChatScope.GROUP:
        return scope
    container = inbound.ref.container
    name = clean_name(inbound.container_name)
    return f"{scope} {container}<{name}>" if name else f"{scope} {container}"


def _content_segments(inbound: InboundEventDTO) -> list[str]:
    """命令段与媒体张数、附文字数各列一段

    - 命令整段抄正文，只把连续空白折成单空格
    - 张数按媒体条目计，同图的多档分辨率只算一条目
    - 正文取的是首条附文，附文单列一段报整组字数
    """
    content = inbound.content
    command = inbound.command
    if command.matched or command.format_error:
        return [f"[{_COMMAND_LABEL} {_SPACE_RUN.sub(' ', content.text.strip())}]"]

    if not content.media:
        return [f"[{_TEXT_LABEL} {len(content.text)}{_TEXT_UNIT}]"]

    counts: dict[ContentKind, int] = {}
    for entry in content.media:
        counts[entry.kind] = counts.get(entry.kind, 0) + 1

    segments = [
        f"[{_KIND_LABELS.get(kind, _UNKNOWN)} {total}"
        f"{_MEASURES.get(kind, _DEFAULT_MEASURE)}]"
        for kind, total in counts.items()
    ]
    caption_chars = sum(len(entry.caption) for entry in content.media)
    if caption_chars:
        segments.append(f"[{_CAPTION_LABEL} {caption_chars}{_TEXT_UNIT}]")
    return segments


class LoggingMiddleware:
    """访问日志中间件

    - 读归一化中间件写入的上下文，整组相册只点一次
    - 不继承引擎基类，只按 handler、event、data 三参被调用
    """

    def __init__(self) -> None:
        # 使用专属子 Logger，便于在日志中区分中间件产生的记录
        self._logger = get_logger("Middleware")

    async def __call__(
        self,
        handler: Callable[..., Awaitable[Any]],
        event: object,
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

        - 形如：群聊 g100123<测试群> [张三|456] （引用 [李四|123]：[文本 2字]）[图片 2张]
        - 形如：私聊 [张三|456] [命令 /grant 12345]
        - 标注帧与模型侧同形，内容槽除命令外只报体量
        """
        mark = speaker_mark(inbound.principal.user, inbound.display_name)
        tokens = " ".join(_content_segments(inbound))
        body = f"{_reply_segment(inbound)}{tokens}"
        segments = (_head_segment(inbound), mark, body)

        return " ".join(segment for segment in segments if segment)
