# src/plugins/AI/handlers/_auth.py
"""黑名单命令（内部实现）

- /on：移出黑名单，开启对话
- /off：加入黑名单，关闭对话
"""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from ... import messages as msgs
from ..services import get_black_list, save_black_list
from ..utils import get_name

auth = Router()

# ==================== /off 对话关闭命令 ====================


@auth.message(Command("off"))
async def turn_off(message: Message) -> None:
    """将当前用户加入黑名单"""
    user = get_name(message)
    black_list = await get_black_list()

    if user not in black_list:
        black_list.append(user)
        await save_black_list(black_list)
        await message.answer(msgs.BLACKLIST_ADDED.format(user=user))
    else:
        await message.answer(msgs.BLACKLIST_EXISTS.format(user=user))


# ==================== /on 对话开启命令 ====================


@auth.message(Command("on"))
async def turn_on(message: Message) -> None:
    """将当前用户移出黑名单"""
    user = get_name(message)
    black_list = await get_black_list()
    if user in black_list:
        black_list.remove(user)
        await save_black_list(black_list)
        await message.answer(msgs.BLACKLIST_REMOVED.format(user=user))
    else:
        await message.answer(msgs.BLACKLIST_ABSENT.format(user=user))
