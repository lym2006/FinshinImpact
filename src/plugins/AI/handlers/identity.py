# src/plugins/AI/handlers/identity.py
"""
身份更改与系统指令路由层

负责：
- /change 命令：通过 FSM 多步修改 AI 身份与名字
- /system 命令：以 system 角色注入系统指令
"""

from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, User

from ..core import build_message, get_name, session_guard, user_sessions

identity = Router()


# ==================== 1. FSM 状态定义 ====================
class Chg(StatesGroup):
    """身份修改流程状态组"""

    name = State()
    identity = State()


class Sys(StatesGroup):
    """系统注入流程状态组"""

    input = State()


# ==================== 2. 内部辅助函数 ====================
def _make_mention(user: User) -> str:
    """生成安全的 Markdown V2 提及链接"""
    user_name = user.username or user.full_name
    safe_name = (
        user_name.replace("_", "\\_")
        .replace("*", "\\*")
        .replace("[", "\\[")
        .replace("]", "\\]")
    )
    return f"[{safe_name}](tg://user?id={user.id})"


# ==================== 3. /change 身份修改命令 ====================
@identity.message(Command("change"))
async def input_name(message: Message, state: FSMContext) -> None:
    """触发修改身份流程"""
    await message.answer("🎭 请输入新身份的名字")
    await state.set_state(Chg.name)


@identity.message(StateFilter(Chg.name))
async def input_identity(message: Message, state: FSMContext) -> None:
    """接收名字，等待描述"""
    if (new_name := message.text) is None:
        await message.answer("⚠️ 请输入有效的文本")
        return

    await state.update_data(name=new_name)
    await message.answer("📝 请输入新身份的描述")
    await state.set_state(Chg.identity)


@identity.message(StateFilter(Chg.identity))
@session_guard
async def change_identity(message: Message, state: FSMContext) -> None:
    """接收描述，完成身份设置"""
    if (new_identity := message.text) is None:
        await message.answer("⚠️ 请输入有效的文本")
        return

    # 防御性获取，防止 FSM 状态丢失导致 KeyError
    tmp = await state.get_data()
    name = tmp.get("name", "未知")
    user = get_name(message)

    # 注入系统指令
    user_sessions[user].message.append(
        build_message("system", f"更改你的身份，你现在是{new_identity}，名字叫{name}")
    )

    if (from_user := message.from_user) is None:
        await message.answer("✅ 身份设置成功")
    else:
        mention = _make_mention(from_user)
        await message.answer(
            f"{mention}，你的机器人「{name}」已准备好，可以开始对话。",
            parse_mode=ParseMode.MARKDOWN_V2,
        )

    await state.clear()


# ==================== 4. /system 系统注入命令 ====================
@identity.message(Command("system"))
async def pre_system(message: Message, state: FSMContext) -> None:
    """触发系统指令输入"""
    await message.answer("💻 你想以system身份输入什么内容")
    await state.set_state(Sys.input)


@identity.message(StateFilter(Sys.input))
@session_guard
async def post_to_system(message: Message, state: FSMContext) -> None:
    """接收并注入系统指令"""
    if (text := message.text) is None:
        await message.answer("⚠️ 请重新输入文本")
        return

    user = get_name(message)
    user_sessions[user].message.append(build_message("system", text))
    await message.answer("✅ 系统指令注入成功")
    await state.clear()
