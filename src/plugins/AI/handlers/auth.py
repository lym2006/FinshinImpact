from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

from ..core import get_name
from ..services import get_black_list,save_black_list

auth=Router()

@auth.message(Command('off'))
async def turn_off(message:Message):
    user=get_name(message)
    black_list=get_black_list()
    if user not in black_list:
        black_list.append(user)
        save_black_list(black_list)
        await message.answer(f"成功将用户{user}写入黑名单")
    else:
        await message.answer(f"用户{user}已存在黑名单内")

@auth.message(Command('on'))
async def turn_on(message:Message):
    user=get_name(message)
    black_list=get_black_list()
    if user in black_list:
        black_list.remove(user)
        save_black_list(black_list)
        await message.answer(f"成功将用户{user}移除黑名单")
    else:
        await message.answer(f"用户{user}不存在黑名单内")