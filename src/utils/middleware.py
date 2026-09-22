# src/utils/middleware.py
"""日志中间件（内部实现）

- 定义访问与异常统一记录管道
"""

from collections.abc import Awaitable, Callable
from typing import Any, cast

from aiogram import BaseMiddleware
from aiogram.enums import ChatType, ContentType
from aiogram.types import Message, TelegramObject, Update

from .logger import get_logger


class LoggingMiddleware(BaseMiddleware):
    """访问日志中间件

    拦截更新事件，格式化输出访问日志。
    """

    # 聊天类型中文映射（类级别常量，避免重复创建）
    _CHAT_TYPE_LABELS: dict[ChatType, str] = {
        ChatType.PRIVATE: "私聊",
        ChatType.GROUP: "群组",
        ChatType.SUPERGROUP: "超级群",
        ChatType.CHANNEL: "频道",
    }

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
        # 类型安全检查：仅处理标准的 Update 事件
        if not isinstance(event, Update):
            return await handler(event, data)

        event = cast(Update, event)

        # 消息过滤：仅记录包含 Message 的事件（忽略回调、预检等）
        if event.message is None:
            return await handler(event, data)

        # 构建日志条目并输出
        try:
            message = cast(Message, event.message)
            log_entry = self._build_log_entry(message)
            self._logger.info(log_entry)

        except Exception as e:
            # 记录中间件自身的异常
            self._logger.send_error("LoggingMiddleware 执行出错", e)

        # 无论日志记录是否成功，都放行事件给下游 Handler
        return await handler(event, data)

    def _build_log_entry(self, message: Message) -> str:
        """构建日志条目

        形如：超级群[-100123]<测试群> | 用户123<张三> 发送[长度：5]文本：Hi
        """
        chat = message.chat
        user = message.from_user
        sender_chat = message.sender_chat

        # 解析聊天信息
        # 优先使用群组标题，其次使用个人名，兜底为"未知聊天"
        chat_name = chat.title or chat.first_name or "未知聊天"
        # 将 ChatType 枚举映射为中文标签
        chat_label = self._CHAT_TYPE_LABELS.get(ChatType(chat.type), "未知")
        chat_info = f"{chat_label}[{chat.id}]<{chat_name}>"

        # 解析发送者信息
        if user:
            # 真实用户发送：优先全名，其次名，兜底为"无名氏"
            user_name = user.full_name or user.first_name or "无名氏"
            sender_info = f"用户{user.id}<{user_name}>"
        elif sender_chat:
            # 频道/匿名管理员发送
            sender_name = sender_chat.title or "未知来源"
            sender_info = f"匿名/频道[{sender_chat.id}]<{sender_name}>"
        else:
            # 系统消息或未知来源
            sender_info = "系统/未知"

        # 解析内容预览
        content_type = message.content_type
        reply_mark = " [回复]" if message.reply_to_message else ""

        match content_type:
            case ContentType.TEXT:
                # 文本消息：截取前60个字符作为预览，并标注长度和是否为回复
                text = message.text or ""
                preview = (text[:60] + "...") if len(text) > 60 else text
                content_preview = f"[长度：{len(text)}] 文本：{preview}"
            case ContentType.DOCUMENT:
                doc = message.document
                detail = f"({name})" if doc and (name := doc.file_name) else ""
                content_preview = f"文档消息：{detail}"
            case ContentType.PHOTO:
                content_preview = (
                    f"图片消息：{len(message.photo) if message.photo else 0}张"
                )
            case ContentType.AUDIO:
                content_preview = "音频消息"
            case ContentType.VOICE:
                content_preview = "语音消息"
            case ContentType.ANIMATION:
                content_preview = "动图消息"
            case _:
                content_preview = f"{content_type}消息"

        # 组装最终日志
        return f"{chat_info} | {sender_info} 发送{reply_mark}{content_preview}"
