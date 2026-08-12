import copy
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message,FSInputFile

from ..config import ini,cupa
from ..core import user_session,session_guard,get_name

history=Router()

@history.message(Command('history'))
@session_guard
async def show_history(message:Message):
    user=get_name(message)
    file_path=cupa/f"{user}.md"
    await message.answer_document(
        document=FSInputFile(file_path),
        caption="📄 这是您最近的对话历史记录"
    )
    file_path.unlink(missing_ok=True)

@history.message(Command('clear'))
@session_guard
async def clear_history(message:Message):
    user=get_name(message)
    user_session[user]['message']=copy.deepcopy(ini)
    await message.answer("记忆清除成功")

@history.message(Command('md'))
@session_guard
async def send_markdown(message:Message):
    user=get_name(message)
    if user_session[user]['md']:
        await message.answer_photo(FSInputFile(cupa/f'{user}.png'))
    else:
        await message.answer("没有对话")