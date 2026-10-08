# src/plugins/AI/core/_tasks.py
"""任务队列

- 定义 Telegram 消息安全操作
- 实现异步任务队列管理
"""

import asyncio
from collections import deque

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message

from exceptions import AITaskStoppedError

from .models import TaskItem


class TelegramTaskItem(TaskItem):
    """注入 bot 的任务载体"""

    def __init__(self, message: Message, bot: Bot) -> None:
        super().__init__(
            message=message,
            chat_id=message.chat.id,
            ori_id=message.message_id,
            type_=message.chat.type,
        )
        self.bot = bot

    async def is_deleted(self) -> bool:
        """探测消息是否已删除"""
        try:
            await self.bot.edit_message_text(
                text="dummy", chat_id=self.chat_id, message_id=self.ori_id
            )
            return False
        except TelegramAPIError as e:
            return "message to edit not found" in str(e)

    async def safe_reply(self, msg: str) -> Message:
        """回复原消息

        - 原消息被删除则抛出 TaskStoppedError
        """
        if await self.is_deleted():
            raise AITaskStoppedError() from None

        try:
            return await self.message.reply(msg)
        except TelegramAPIError as e:
            if any(
                i in str(e).lower()
                for i in ["message to be replied not found", "message_invalid_id"]
            ):
                raise AITaskStoppedError() from None
            else:
                raise


class TaskQueue:
    """管理消息任务的队列"""

    def __init__(self) -> None:
        self._queue: deque[TelegramTaskItem] = deque()
        self._lock = asyncio.Lock()

    async def add_task(self, task: TelegramTaskItem) -> None:
        """向队列尾部添加一个任务"""
        async with self._lock:
            self._queue.append(task)

    async def peek_front(self) -> TelegramTaskItem | None:
        """查看队首任务但不将其移出队列"""
        async with self._lock:
            return self._queue[0] if self._queue else None

    async def pop_front(self) -> TelegramTaskItem | None:
        """从队首弹出一个任务"""
        async with self._lock:
            return self._queue.popleft() if self._queue else None

    @property
    def size(self) -> int:
        """获取当前队列中的任务数量"""
        return len(self._queue)
