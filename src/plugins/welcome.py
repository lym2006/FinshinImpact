import time
import logging
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

#from ..utils import get_started

logger=logging.getLogger("Bot.Plugins.router")
router=Router()

@router.message(Command("start"))
async def command_start_handler(message:Message):
    user=message.from_user.id if message.from_user else None
    if not user:
        logger.warning("⚠️ 无法获取用户 ID")
        return
    #get_started(user)
    await message.answer(
        "你好，我是基于aiogram开发的机器人Fool\n"
        "你可以输入\"/help\"获取功能列表，现在与我开始对话吧~"
    )
    logger.info(f"✅️ 用户开始对话: {user}")

@router.message(Command('time'))
async def now_time(message:Message):
    await message.answer(time.strftime("%Y-%m-%d %H:%M:%S",time.localtime()))

__all__=["router"]