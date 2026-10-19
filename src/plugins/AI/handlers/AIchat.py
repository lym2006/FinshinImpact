import logging
import asyncio
from aiogram import Router,Bot
from aiogram.types import Message
from aiogram.filters import Filter
from aiogram.enums import ChatType,ContentType

from ..config import GROUP_TRIGGERS
from ..core import (
        user_session,active_tasks,TaskItem,
        get_name,session_guard,retry_sending
    )
from ..services import monitor_loop,get_black_list

chat=Router()
logger=logging.getLogger("Bot.Plugins.AI")
user_locks={}

class ChatFilter(Filter):
    async def __call__(self,message:Message)->bool:
        if message.content_type!=ContentType.TEXT:
            return False
        assert message.text
        match message.chat.type:
            case ChatType.PRIVATE:
                is_command=message.text.startswith('/')
                return not is_command
            case ChatType.GROUP|ChatType.SUPERGROUP:
                return any(keyword in message.text.lower() for keyword in GROUP_TRIGGERS)
            case _:
                return False

@chat.message(ChatFilter())
@session_guard
@retry_sending()
async def AIchat(message:Message,bot:Bot):
    user=get_name(message)
    black_list=get_black_list()
    if user in black_list:
        return
    session=user_session[user]
    queue=session['queue']
    task=TaskItem(message,bot)
    if user not in user_locks:
        user_locks[user]=asyncio.Lock()
    lock=user_locks[user]
    async with lock:
        await queue.add_task(task)
        if queue.size==1 and not session['is_active']:
            preview="🧠 正在思考中"
            if task.type in [ChatType.GROUP,ChatType.SUPERGROUP]:
                preview+="\n群组不推送思考过程，如需要使用 /history 命令查看"
        else:
            preview="⏳ 请等待排队"
        try:
            sent=await task.safe_reply(preview)
        except Exception as e:
            if str(e):
                logger.warning("🚨 消息任务不存在")
            else:
                logger.error(f"❌ 任务初始化错误：{e}")
            return
        task.status_id=sent.message_id
        if not session.get('is_active'):
            logger.info(f"{user} 监控循环启动")
            session['is_active']=True
            monitor_task=asyncio.create_task(monitor_loop(user))
            active_tasks.add(monitor_task)
            monitor_task.add_done_callback(active_tasks.discard)
        else:
            logger.info(f"用户 {user} 新任务入队，当前长度: {queue.size}")