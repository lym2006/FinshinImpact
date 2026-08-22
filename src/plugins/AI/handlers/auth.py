# src/plugins/AI/handlers/auth.py
"""
权限控制路由层

负责：
- /off 命令：将当前用户加入黑名单
- /on 命令：将当前用户移出黑名单
"""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from ..core import get_name
from ..services import get_black_list, save_black_list

auth = Router()


# ==================== 1. /off 对话关闭命令 ====================
@auth.message(Command("off"))
async def turn_off(message: Message) -> None:
    """将当前用户加入黑名单"""
    user = get_name(message)
    black_list = await get_black_list()

    if user not in black_list:
        black_list.append(user)
        await save_black_list(black_list)
        await message.answer(f"🚫 成功将用户 [{user}] 写入黑名单")
    else:
        await message.answer(f"🚫 用户 [{user}] 已存在黑名单内")


# ==================== 2. /on 对话开启命令 ====================
@auth.message(Command("on"))
async def turn_on(message: Message) -> None:
    """将当前用户移出黑名单"""
    user = get_name(message)
    black_list = await get_black_list()
    if user in black_list:
        black_list.remove(user)
        await save_black_list(black_list)
        await message.answer(f"✅ 成功将用户 [{user}] 移出黑名单")
    else:
        await message.answer(f"⚠️ 用户 [{user}] 不存在黑名单内")
