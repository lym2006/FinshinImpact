# src/plugins/AI/handlers/_ai_chat.py
"""对话处理

- 拦下无权私聊的成员，其余场景自动应答
- 提供对话任务入队分发
"""

from aiogram import Router
from aiogram.filters import Filter
from aiogram.types import Message

from core.domain import ChatScope, CommandRole
from services.context import HandlerContext
from utils import get_logger

from ...messages import BotMessage
from ..config import ai_config
from ..core import role_of, session_guard
from ..services import handle_ai_chat

ai_chat = Router()

_logger = get_logger("Plg.AI.Chat")


class _PrivateGate(Filter):
    """拦下无权私聊者发来的普通文本

    - 私聊场景要管理员以上，成员引回群里
    - 命令形态不接，档位由各命令自己判
    """

    async def __call__(self, raw: Message, ctx: HandlerContext | None = None) -> bool:
        """判定是否为无权私聊的成员"""
        if ctx is None:
            return False
        event = ctx.event
        command = event.command
        if command.matched or command.format_error:
            return False
        if event.scope != ChatScope.PRIVATE:
            return False
        if event.content.media or not event.content.text:
            return False
        return await role_of(event.principal) == CommandRole.MEMBER


class _ChatFilter(Filter):
    """筛选需要 AI 处理的文本消息

    - 命令与非法形态一律让行，命令路由优先
    - 群聊按 @ 点名、引用本机器人、触发词三档降级命中
    """

    async def __call__(self, raw: Message, ctx: HandlerContext | None = None) -> bool:
        """判断消息是否应该触发 AI 聊天"""
        if ctx is None:
            return False
        event = ctx.event

        # 命令格式错误
        command = event.command
        if command.matched or command.format_error:
            return False

        # 非纯文字或无文本
        content = event.content
        if content.media or not content.text:
            return False

        match event.scope:
            case ChatScope.PRIVATE:
                # 私聊：能走到这里的就是有权限的，非命令文本全部接管
                return True
            case ChatScope.GROUP:
                # 群聊：点名或引用本机器人直接应答，否则须命中触发词（忽略大小写）
                if event.is_mention_bot or event.reply_to_bot:
                    return True
                return any(
                    keyword.lower() in event.content.text.lower()
                    for keyword in ai_config.group_triggers
                )
            case _:
                return False  # 其他类型一律忽略


@ai_chat.message(_PrivateGate())
async def deny_private(raw: Message, ctx: HandlerContext) -> None:
    """私聊门槛回执"""
    _logger.info(f"{ctx.event.principal.key} 无权私聊，已拦下")
    await ctx.answer(BotMessage.CHAT_PRIVATE_DENIED)


@ai_chat.message(_ChatFilter())
@session_guard
async def process_ai_chat(raw: Message, ctx: HandlerContext) -> None:
    """AI 聊天核心处理器"""
    await handle_ai_chat(ctx)
