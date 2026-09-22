# src/plugins/AI/handlers/_history.py
"""历史命令（内部实现）

- /history：发送对话记录文档
- /clear：清除当前会话记忆
- /md：以图片形式发送上次回复
"""

from pathlib import Path

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import FSInputFile, Message

from ... import messages as msgs
from ..config import ai_config
from ..core import session_guard, user_sessions
from ..utils import get_name

history = Router()

# ==================== 内部辅助函数 ====================


def _get_file_path(user: str) -> Path:
    return ai_config.record_dir / f"temp/{user}.md"


# ==================== /history 历史查询命令 ====================


@history.message(Command("history"))
@session_guard
async def show_history(message: Message) -> None:
    """发送历史记录（以文档形式）"""
    user = get_name(message)
    file_path = _get_file_path(user)

    if not file_path.exists():
        await message.answer(msgs.NO_HISTORY)
        return

    await message.answer_document(
        document=FSInputFile(file_path), caption=msgs.HISTORY_CAPTION
    )


# ==================== /clear 记忆清除命令 ====================


@history.message(Command("clear"))
@session_guard
async def clear_history(message: Message) -> None:
    """清除记忆"""
    user = get_name(message)
    file_path = _get_file_path(user)

    user_sessions[user].message = list(ai_config.init)
    file_path.unlink(missing_ok=True)
    await message.answer(msgs.MEMORY_CLEARED)


# ==================== /md 图片发送命令 ====================


@history.message(Command("md"))
@session_guard
async def send_markdown(message: Message) -> None:
    """图片形式发送回复"""
    user = get_name(message)
    img_path = ai_config.record_dir / f"temp/{user}.png"

    if user_sessions[user].md_status and img_path.exists():
        await message.answer_photo(FSInputFile(img_path))
    else:
        await message.answer(msgs.NO_MD_CONTENT)
