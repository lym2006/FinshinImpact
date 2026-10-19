# src/plugins/AI/handlers/_ai_chat.py
"""对话处理（内部实现）

- 实现私聊自动响应与群聊拦截
- 提供对话任务入队分发
"""

from aiogram import Bot, Router
from aiogram.enums import ChatType, ContentType
from aiogram.filters import Filter
from aiogram.types import Message

from ..config import ai_config
from ..core import session_guard
from ..services import handle_ai_chat
from ..utils import retry_sending

ai_chat = Router()

# ==================== 自定义过滤器 ====================


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
                return any(
                    keyword.lower() in text.lower()
                    for keyword in ai_config.group_triggers
                )
            case _:
                return False  # 其他类型一律忽略


# ==================== AI 聊天路由处理函数 ====================


@ai_chat.message(ChatFilter())
@session_guard
@retry_sending()
async def process_ai_chat(message: Message, bot: Bot) -> None:
    """AI 聊天核心处理器"""
    await handle_ai_chat(message, bot)
