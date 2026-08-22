# src/plugins/welcome.py
"""
欢迎与基础指令插件

提供：
- /start 欢迎语
- /time 时间查询
"""

import logging
import time

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

logger = logging.getLogger("Bot.Plugins.Welcome")
router = Router()


# ==================== 1. /start 开始命令 ====================
@router.message(Command("start"))
async def command_start_handler(message: Message) -> None:
    """发送欢迎语并记录用户上线日志"""
    user_id = message.from_user.id if message.from_user else None
    if user_id is None:
        logger.warning("🚨 无法获取用户 ID")
        return

    # TODO: 后续可在此处调用 get_started(user_id) 初始化用户数据
    await message.answer(
        "你好，我是基于aiogram开发的机器人Fool\n"
        '你可以输入"/help"获取功能列表，现在与我开始对话吧~'
    )
    logger.info(f"✅️ 用户开始对话: {user_id}")


# ==================== 2. /time 时间查询命令 ====================
@router.message(Command("time"))
async def now_time(message: Message) -> None:
    """返回服务器当前时间"""
    await message.answer(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))


# ==================== 3. 模块导出声明 ====================

__all__ = ["router"]
