# src/plugins/AI/core/_tasks.py
"""任务队列（内部实现）

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

# ==================== Telegram 任务执行器 ====================


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

    async def safe_delete(self) -> None:
        """删除状态消息

        消息已不存在则静默失败。
        """
        try:
            await self.safe_draft("用户主动停止，正在清除消息...")
            await self.bot.delete_message(
                chat_id=self.chat_id, message_id=self.status_id
            )
        except TelegramAPIError:
            # 消息可能已经被删除，无需处理，静默失败
            pass

    async def safe_reply(self, msg: str) -> Message:
        """回复原消息

        原消息被删除则抛出 TaskStoppedError。
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

    async def safe_edit(self, msg: str) -> None:
        """编辑状态消息

        编辑失败则降级为回复新消息。
        """
        if await self.is_deleted():
            raise AITaskStoppedError() from None

        try:
            await self.bot.edit_message_text(
                text=msg, chat_id=self.chat_id, message_id=self.status_id
            )
        except TelegramAPIError as e:
            if "message is not modified" in str(e):
                # 内容未修改，直接忽略
                return

            if any(
                i in str(e)
                for i in ["message to edit not found", "message can't be edited"]
            ):
                # 降级处理：尝试回复新消息
                new_msg = await self.safe_reply(msg)
                self.status_id = new_msg.message_id
            else:
                raise

    async def safe_draft(self, text: str) -> bool:
        """发送草稿消息

        失败时静默返回 False。
        """
        try:
            return await self.bot.send_message_draft(
                chat_id=self.chat_id, draft_id=self.draft_id, text=text
            )
        except Exception:
            return False


# ==================== 异步安全任务队列 ====================


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
