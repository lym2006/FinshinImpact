# src/plugins/AI/handlers/ai_chat.py
"""
AI 聊天路由层

负责：
- 私聊文本消息的自动响应
- 群聊关键词触发与拦截
- 核心对话任务的入队分发
"""

from aiogram import Bot, Router
from aiogram.enums import ChatType, ContentType
from aiogram.filters import Filter
from aiogram.types import Message

from ..core import (
    retry_sending,
    session_guard,
)
from ..core.config import GROUP_TRIGGERS
from ..services import handle_ai_chat

ai_chat = Router()


# ==================== 1. 自定义过滤器 ====================
class ChatFilter(Filter):
    """筛选出需要 AI 处理的文本消息"""

    async def __call__(self, message: Message) -> bool:
        """判断消息是否应该触发 AI 聊天"""
        if message.content_type != ContentType.TEXT:
            return False

        assert message.text is not None
        text = message.text

        match message.chat.type:
            case ChatType.PRIVATE:
                # 私聊：排除以 "/" 开头的命令消息
                is_command = text.startswith("/")
                return not is_command
            case ChatType.GROUP | ChatType.SUPERGROUP:
                # 群聊：必须包含配置的触发词（忽略大小写）
                return any(keyword in text.lower() for keyword in GROUP_TRIGGERS)
            case _:
                # 其他类型一律忽略
                return False


# ==================== 2. AI 聊天路由处理函数 ====================
@ai_chat.message(ChatFilter())
@session_guard
@retry_sending()
async def process_ai_chat(message: Message, bot: Bot) -> None:
    """AI 聊天核心处理器

    处理消息入队、状态提示与监控循环启动
    """
    await handle_ai_chat(message, bot)
