# src/plugins/AI/services/ai_chat.py
"""
AI 聊天业务逻辑层

负责：
- 处理消息入队
- 状态提示
- 监控循环启动
"""

import asyncio
import logging

from aiogram import Bot
from aiogram.enums import ChatType
from aiogram.types import Message

from ..core import (
    TelegramTaskItem,
    active_tasks,
    get_name,
    task_queues,
    user_sessions,
)
from ..state import user_locks
from .blacklist import get_black_list
from .monitor import monitor_loop

logger = logging.getLogger("Bot.Plugins.AI")


# ==================== 1. 内部辅助函数 ====================
def _get_preview_text(task: TelegramTaskItem, is_first_task: bool) -> str:
    """根据任务状态生成提示文案"""
    if is_first_task:
        preview = "🧠 正在思考中"
        if task.type_ in [ChatType.GROUP, ChatType.SUPERGROUP]:
            preview += "\n群组不推送思考过程，如需要使用 /history 命令查看"
        return preview
    return "⏳ 请等待排队"


# ==================== 2. 核心业务处理 ====================
async def handle_ai_chat(message: Message, bot: Bot) -> None:
    """AI 聊天核心业务处理

    处理消息入队、状态提示与监控循环启动。
    """
    user = get_name(message)

    if user in await get_black_list():
        return

    session = user_sessions[user]
    queue = task_queues[user]
    task = TelegramTaskItem(message, bot)

    lock = user_locks[user]
    async with lock:
        await queue.add_task(task)

        preview = _get_preview_text(task, queue.size == 1 and not session.is_active)

        try:
            sent = await task.safe_reply(preview)
        except Exception as e:
            logger.error(f"❌ 任务初始化/发送提示失败：{e}")
            return

        task.status_id = sent.message_id

        if not session.is_active:
            logger.info(f"{user} 监控循环启动")
            session.is_active = True
            monitor_task = asyncio.create_task(monitor_loop(user))
            active_tasks.add(monitor_task)
            monitor_task.add_done_callback(active_tasks.discard)
        else:
            logger.info(f"用户 {user} 新任务入队，当前长度: {queue.size}")
