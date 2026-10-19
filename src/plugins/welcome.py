# src/plugins/welcome.py
"""欢迎插件（内部实现）

- /start：返回欢迎语
- /time：查询当前时间
"""

import time

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from utils import get_logger

from . import messages as msgs

logger = get_logger("Plg.Welcome")
router = Router()
__all__ = ["router"]

# ==================== /start 开始命令 ====================


@router.message(Command("start"))
async def command_start_handler(message: Message) -> None:
    """发送欢迎语并记录用户上线日志"""
    user_id = message.from_user.id if message.from_user else None
    if user_id is None:
        logger.error("无法获取用户 ID")
        return

    # TODO: 后续可在此处调用 get_started(user_id) 初始化用户数据
    await message.answer(msgs.WELCOME)
    logger.info(f"用户 {user_id} 发起对话")


# ==================== /time 时间查询命令 ====================


@router.message(Command("time"))
async def now_time(message: Message) -> None:
    """返回服务器当前时间"""
    await message.answer(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
