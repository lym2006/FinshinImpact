import asyncio
from collections import deque
from aiogram import Bot
from aiogram.types import Message
from aiogram.exceptions import TelegramAPIError

class TaskStopped(Exception):
    pass

class TaskItem:
    def __init__(self,message:Message,bot:Bot):
        self.bot=bot
        self.message=message
        self.chat_id=message.chat.id
        self.ori_id=message.message_id
        self.type:str=message.chat.type
        self.status_id:int
        self.draft_id:int
        self.last_draft_time:float

    async def is_deleted(self) -> bool:#尝试编辑用户原消息来判断消息是否被删除
        try:
            await self.bot.edit_message_text(
                text="dummy",
                chat_id=self.chat_id,
                message_id=self.ori_id
            )
            return False
        except TelegramAPIError as e:
            if "message to edit not found" in str(e):
                return True
            return False
        
    async def safe_delete(self):#安全删除状态消息
        try:
            await self.safe_draft("用户主动停止，正在清除消息...")
            await self.bot.delete_message(
                chat_id=self.chat_id,
                message_id=self.status_id
            )
        except:
            raise

    async def safe_reply(self,msg:str):#安全回复原消息
        if await self.is_deleted():
            raise TaskStopped()
        try:
            new_msg=await self.message.reply(msg)
            return new_msg
        except Exception as e:
            if any(i in str(e).lower() for i in ["message to be replied not found","message_invalid_id"]):
                raise TaskStopped()
            else:
                raise e

    async def safe_edit(self,msg:str):#安全编辑状态消息
        if await self.is_deleted():
            raise TaskStopped()
        try:
            await self.bot.edit_message_text(
                text=msg,
                chat_id=self.chat_id,
                message_id=self.status_id
            )
        except TelegramAPIError as e:
            if "message is not modified" in str(e):
                return
            if any(i in str(e) for i in ["message to edit not found","message can't be edited"]):
                try:
                    new_msg=await self.safe_reply(msg)
                except:
                    raise
                self.status_id=new_msg.message_id
            else:
                raise e
        except:
            raise

    async def safe_draft(self,text:str) -> bool:#安全发送草稿
        try:
            success=await self.bot.send_message_draft(
                chat_id=self.chat_id,
                draft_id=self.draft_id,
                text=text
            )
            return success
        except:
            return False


class TaskQueue:
    def __init__(self):
        self._queue:deque[TaskItem]=deque()
        self._lock=asyncio.Lock()

    async def add_task(self,task:TaskItem):#添加任务
        async with self._lock:
            self._queue.append(task)

    async def peek_front(self)->TaskItem|None:#查看队首
        async with self._lock:
            if self._queue:
                return self._queue[0]
            return
        
    async def pop_front(self) -> TaskItem|None:#弹出队首
        async with self._lock:
            if self._queue:
                return self._queue.popleft()
            return


    @property
    def size(self):#获取长度
        return len(self._queue)