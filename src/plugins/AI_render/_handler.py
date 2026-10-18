# src/plugins/AI_render/_handler.py
"""Markdown 图片命令

- /md：以图片形式发送上一次回复
"""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import FSInputFile, Message

from ..AI.config import ai_config
from ..AI.core import session_guard, user_sessions
from ..AI.utils import get_name
from ..messages import BotMessage

md_router = Router()


@md_router.message(Command("md"))
@session_guard
async def send_markdown(message: Message) -> None:
    """图片形式发送回复"""
    user = get_name(message)
    img_path = ai_config.record_dir / f"temp/{user}.png"

    if user_sessions[user].md_status and img_path.exists():
        await message.answer_photo(FSInputFile(img_path))
    else:
        await message.answer(BotMessage.HISTORY_NO_CONTENT)
