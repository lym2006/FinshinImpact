from aiogram import Router
from aiogram.types import Message,User
from aiogram.filters import Command,StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode

from ..core import rc,user_session,session_guard,get_name

identity=Router()

class Chg(StatesGroup):
    name=State()
    identity=State()

def makemention(user:User):
    user_name=user.username or user.full_name
    mention_link=f"[{user_name}](tg://user?id={user.id})"
    return mention_link

@identity.message(Command('change'))
async def input_name(message:Message,state:FSMContext):
    await message.answer("请输入新身份的名字")
    await state.set_state(Chg.name)

@identity.message(StateFilter(Chg.name))
async def input_identity(message:Message,state:FSMContext):
    await state.update_data(name=message.text)
    await message.answer("请输入新身份的描述")
    await state.set_state(Chg.identity)

@identity.message(StateFilter(Chg.identity))
@session_guard
async def changesetting(message:Message,state:FSMContext):
    tmp=await state.get_data()
    name=tmp['name']
    identity=message.text
    user=get_name(message)
    user_session[user]['message'].append(rc("system",f"更改你的身份，你现在是{identity}，名字叫{name}"))
    assert message.from_user,'用户为空'
    await message.answer(f"{makemention(message.from_user)}，你的机器人「{name}」已准备好，可以开始对话。",parse_mode=ParseMode.MARKDOWN_V2)
    await state.clear()

class Sys(StatesGroup):
    input=State()

@identity.message(Command('system'))
async def pre_system(message:Message,state:FSMContext):
    await message.answer("你想以system身份输入什么内容")
    await state.set_state(Sys.input)

@identity.message(StateFilter(Sys.input))
@session_guard
async def post_to_system(message:Message,state:FSMContext):
    if not message.text:
        await message.answer("请重新输入文本")
        return
    user=get_name(message)
    msg=message.text
    user_session[user]['message'].append(rc('system',msg))
    await message.answer("成功输入")
    await state.clear()