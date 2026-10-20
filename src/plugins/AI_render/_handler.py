# src/plugins/AI_render/_handler.py
"""Markdown 图片命令

- /md：以图片形式发送上一次回复
"""

from aiogram import Router
from aiogram.types import Message

from core.domain import ContentKind
from core.dto import OutboundPayloadDTO
from services.context import HandlerContext

from ..AI.config import ai_config
from ..AI.core import session_guard, user_sessions
from ..filters import CommandFilter
from ..messages import BotMessage

md_router = Router()


@md_router.message(CommandFilter("md"))
@session_guard
async def send_markdown(raw: Message, ctx: HandlerContext) -> None:
    """图片形式发送回复"""
    user = ctx.event.principal.key
    img_path = ai_config.record_dir / f"temp/{ctx.event.principal.key}.png"

    if user_sessions[user].md_status and img_path.exists():
        await ctx.answer(
            OutboundPayloadDTO(kind=ContentKind.PHOTO, local_path=str(img_path))
        )
    else:
        await ctx.answer(BotMessage.HISTORY_NO_CONTENT)
