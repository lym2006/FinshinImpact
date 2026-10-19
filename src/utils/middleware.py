import logging
from typing import Callable,Any,Awaitable,cast

from aiogram import BaseMiddleware
from aiogram.types import Message,Update,TelegramObject
from aiogram.enums import ChatType,parse_mode

from .auth import is_blocked#,has_started

class LoggingMiddleware(BaseMiddleware):#用于记录日志
    def __init__(self):
        super().__init__()
        self.logger=logging.getLogger("Bot.Middlewares.Access")
    async def __call__(
        self,
        handler:Callable[[TelegramObject,dict[str,Any]],Awaitable[Any]],
        event:TelegramObject,
        data:dict[str,Any]
    ):
        try:
            if not isinstance(event, Update):
                return await handler(event,data)
            event=cast(Update,event)
            if not event.message:
                return await handler(event,data)
            message:Message=event.message
            chat=message.chat
            user=message.from_user
            sender_chat=message.sender_chat
            content_type=message.content_type
            chat_name=chat.title if chat.title else (chat.first_name or "未知聊天")
            chat_type_map={
                ChatType.PRIVATE:"私聊",
                ChatType.GROUP:"群组",
                ChatType.SUPERGROUP:"超级群",
                ChatType.CHANNEL:"频道"
            }
            chat_label=chat_type_map.get(ChatType(chat.type),"未知")
            chat_info=f"{chat_label}[{chat.id}]<{chat_name}>"
            if user:
                user_name=user.full_name if user.full_name else (user.first_name or "无名氏")
                sender_info=f"用户{user.id}<{user_name}>"
            elif sender_chat:
                sender_name=sender_chat.title or "未知来源"
                sender_info=f"匿名/频道[{sender_chat.id}]<{sender_name}>"
            else:
                sender_info="系统/未知"
            content_preview=""
            if content_type=="text":
                text=message.text or ""
                reply_mark="[回复]" if message.reply_to_message else ""
                text_preview=(text[:60]+"...") if len(text)>60 else text
                content_preview=f"{reply_mark}[长度：{len(text)}]文本：{text_preview}"
            else:
                file_detail=""
                if content_type=="document" and message.document:
                    file_detail=f"({message.document.file_name})"
                elif content_type=="photo":
                    file_detail=f"({len(message.photo) if message.photo else 0}张)"
                content_preview=f"{content_type}消息：{file_detail}".strip()
            log_msg=f"{chat_info} | {sender_info} 发送 {content_preview}"
            self.logger.info(log_msg)
        except Exception as e:
            self.logger.error(f"❌ LoggingMiddleware 执行出错: {e}",exc_info=True)
        return await handler(event,data)

class AuthMiddleware(BaseMiddleware):
    def __init__(self):
        super().__init__()
        self.logger=logging.getLogger("Bot.Middlewares.Auth")
    async def __call__(
        self,
        handler:Callable[[TelegramObject,dict[str, Any]],Awaitable[Any]],
        event:TelegramObject,
        data:dict[str,Any]
    ):
        if not isinstance(event, Update) or not event.message:
            return await handler(event, data)
        message=event.message
        user=message.from_user.id if message.from_user else None
        if not user:
            self.logger.warning("🚨 无法获取用户 ID")
            return
        if is_blocked(user):
            self.logger.warning(f"🚫 拦截黑名单用户: {user}")
            await message.answer("⛔️ 你已被列入黑名单。")
            return
        return await handler(event,data)