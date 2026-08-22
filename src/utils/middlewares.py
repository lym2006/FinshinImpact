# src/utils/middleware.py
"""
全局中间件工具

提供：
- 日志记录中间件
"""

import logging
from collections.abc import Awaitable, Callable
from typing import Any, cast

from aiogram import BaseMiddleware
from aiogram.enums import ChatType
from aiogram.types import Message, TelegramObject, Update


class LoggingMiddleware(BaseMiddleware):
    """
    日志记录中间件

    拦截所有 Telegram 更新事件，提取消息元数据并格式化输出到日志中。
    支持私聊、群组、超级群、频道等多种消息类型的解析。
    """

    def __init__(self):
        super().__init__()
        # 使用专属子 Logger，便于在日志中区分中间件产生的记录
        self.logger = logging.getLogger("Bot.Middlewares")

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ):
        """
        中间件核心入口

        在事件传递给下游 Handler 之前，安全地提取并记录访问日志。
        即使日志记录过程发生异常，也不会阻断事件的正常处理。
        """
        try:
            # 1. 类型安全检查：仅处理标准的 Update 事件
            if not isinstance(event, Update):
                return await handler(event, data)
            event = cast(Update, event)

            # 2. 消息过滤：仅记录包含 Message 的事件（忽略回调、预检等）
            if event.message is None:
                return await handler(event, data)

            # 3. 构建日志条目并输出
            message = cast(Message, event.message)
            log_entry = self._build_log_entry(message)
            self.logger.info(log_entry)

        except Exception as e:
            # 记录中间件自身的异常，exc_info=True 会打印完整堆栈
            self.logger.error(f" LoggingMiddleware 执行出错: {e}", exc_info=True)

        # 4. 无论日志记录是否成功，都放行事件给下游 Handler
        return await handler(event, data)

    def _build_log_entry(self, message: Message) -> str:
        """
        构建格式化的日志条目

        Returns:
            格式化后的日志字符串，例如:
            "超级群[-100123456]<测试群> | 用户123456<张三> 发送 [长度：5]文本：你好啊"
        """
        chat = message.chat
        user = message.from_user
        sender_chat = message.sender_chat

        # --- 1. 解析聊天信息 ---
        # 优先使用群组标题，其次使用个人名，兜底为"未知聊天"
        chat_name = chat.title if chat.title else (chat.first_name or "未知聊天")
        # 将 ChatType 枚举映射为中文标签
        chat_type_map = {
            ChatType.PRIVATE: "私聊",
            ChatType.GROUP: "群组",
            ChatType.SUPERGROUP: "超级群",
            ChatType.CHANNEL: "频道",
        }
        chat_label = chat_type_map.get(ChatType(chat.type), "未知")
        chat_info = f"{chat_label}[{chat.id}]<{chat_name}>"

        # --- 2. 解析发送者信息 ---
        if user:
            # 真实用户发送：优先全名，其次名，兜底为"无名氏"
            user_name = (
                user.full_name if user.full_name else (user.first_name or "无名氏")
            )
            sender_info = f"用户{user.id}<{user_name}>"
        elif sender_chat:
            # 频道/匿名管理员发送
            sender_name = sender_chat.title or "未知来源"
            sender_info = f"匿名/频道[{sender_chat.id}]<{sender_name}>"
        else:
            # 系统消息或未知来源
            sender_info = "系统/未知"

        # --- 3. 解析内容预览 ---
        content_type = message.content_type
        if content_type == "text":
            # 文本消息：截取前60个字符作为预览，并标注长度和是否为回复
            text = message.text or ""
            reply_mark = "[回复]" if message.reply_to_message else ""
            text_preview = (text[:60] + "...") if len(text) > 60 else text
            content_preview = f"{reply_mark}[长度：{len(text)}]文本：{text_preview}"
        else:
            # 非文本消息：记录消息类型及附件详情（如文件名、图片数量）
            file_detail = ""
            if content_type == "document" and message.document:
                file_detail = f"({message.document.file_name})"
            elif content_type == "photo":
                file_detail = f"({len(message.photo) if message.photo else 0}张)"
            content_preview = f"{content_type}消息：{file_detail}".strip()

        # --- 4. 组装最终日志 ---
        return f"{chat_info} | {sender_info} 发送 {content_preview}"
