# src/plugins/AI/handlers/_ai_chat.py
"""对话处理

- 实现私聊自动响应与群聊拦截
- 提供对话任务入队分发
"""

from aiogram import Bot, Router
from aiogram.enums import ChatType, ContentType
from aiogram.filters import Filter
from aiogram.types import Message

from services import HandlerContext

from ..config import ai_config
from ..core import session_guard
from ..services import handle_ai_chat
from ..utils import retry_sending

ai_chat = Router()


class _ChatFilter(Filter):
    """筛选需要 AI 处理的文本消息

    - 命令与非法形态一律让行，命令路由优先
    - 群聊按 @ 点名、引用本机器人、触发词三档降级命中
    """

    async def __call__(
        self, message: Message, ctx: HandlerContext | None = None
    ) -> bool:
        """判断消息是否应该触发 AI 聊天"""
        if message.content_type != ContentType.TEXT or ctx is None:
            return False

        assert message.text is not None
        text = message.text

        command = ctx.event.command
        if command.matched or command.format_error:
            return False

        match message.chat.type:
            case ChatType.PRIVATE:
                # 私聊：非命令文本全部接管
                return True
            case ChatType.GROUP | ChatType.SUPERGROUP:
                # 群聊：点名或引用本机器人直接应答，否则须命中触发词（忽略大小写）
                if ctx.event.is_mention_bot or ctx.event.reply_to_bot:
                    return True
                return any(
                    keyword.lower() in text.lower()
                    for keyword in ai_config.group_triggers
                )
            case _:
                return False  # 其他类型一律忽略


@ai_chat.message(_ChatFilter())
@session_guard
@retry_sending()
async def process_ai_chat(message: Message, bot: Bot) -> None:
    """AI 聊天核心处理器"""
    await handle_ai_chat(message, bot)
