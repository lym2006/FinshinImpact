# src/plugins/AI/handlers/_history.py
"""历史命令

- /history：发送对话记录文档
- /clear：清除当前会话记忆
"""

from pathlib import Path

from aiogram import Router
from aiogram.types import Message

from core.domain import ContentKind
from core.dto import OutboundPayloadDTO
from services.context import HandlerContext

from ...filters import CommandFilter
from ...messages import BotMessage
from ..config import ai_config
from ..core import session_guard, user_sessions

history = Router()


def _get_file_path(stem: str) -> Path:
    return ai_config.record_dir / f"temp/{stem}.md"


@history.message(CommandFilter("history"))
@session_guard
async def show_history(raw: Message, ctx: HandlerContext) -> None:
    """发送历史记录"""
    stem = ctx.event.principal.key
    file_path = _get_file_path(stem)

    if not file_path.exists():
        await ctx.answer(BotMessage.HISTORY_EMPTY)
        return

    await ctx.answer(
        OutboundPayloadDTO(
            kind=ContentKind.DOCUMENT,
            text=BotMessage.HISTORY_CAPTION,
            local_path=str(file_path),
            file_name=file_path.name,
        )
    )


@history.message(CommandFilter("clear"))
@session_guard
async def clear_history(raw: Message, ctx: HandlerContext) -> None:
    """清除记忆"""
    user = ctx.event.principal.key
    file_path = _get_file_path(ctx.event.principal.key)
    user_sessions[user].message = list(ai_config.init)
    file_path.unlink(missing_ok=True)
    await ctx.answer(BotMessage.HISTORY_MEMORY_CLEARED)
