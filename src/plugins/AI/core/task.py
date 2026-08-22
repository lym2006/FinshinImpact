# src/plugins/AI/core/task.py
"""
AI 核心任务执行与队列管理

提供：
- Telegram 消息安全操作封装（编辑/回复/删除/草稿）
- 异步安全的任务队列管理
"""

import asyncio
from collections import deque

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message

from utils.exceptions import TaskStoppedError

from .models import TaskItem


# ==================== 1. Telegram 任务执行器 ====================
class TelegramTaskItem(TaskItem):
    """Telegram 任务执行器，继承 TaskItem 的所有数据并注入 bot 实例以执行操作"""

    def __init__(self, message: Message, bot: Bot):
        super().__init__(
            message=message,
            chat_id=message.chat.id,
            ori_id=message.message_id,
            type_=message.chat.type,
        )
        self.bot = bot

    async def is_deleted(self) -> bool:
        """通过尝试编辑原消息来探测消息是否已被删除"""
        try:
            await self.bot.edit_message_text(
                text="dummy", chat_id=self.chat_id, message_id=self.ori_id
            )
            return False
        except TelegramAPIError as e:
            return "message to edit not found" in str(e)

    async def safe_delete(self) -> None:
        """安全删除状态消息，若消息已不存在则静默失败"""
        try:
            await self.safe_draft("用户主动停止，正在清除消息...")
            await self.bot.delete_message(
                chat_id=self.chat_id, message_id=self.status_id
            )
        except TelegramAPIError:
            # 消息可能已经被删除，无需处理，静默失败
            pass

    async def safe_reply(self, msg: str) -> Message:
        """安全回复原消息，若原消息被删除则抛出 TaskStoppedError"""
        if await self.is_deleted():
            raise TaskStoppedError()

        try:
            return await self.message.reply(msg)
        except TelegramAPIError as e:
            if any(
                i in str(e).lower()
                for i in ["message to be replied not found", "message_invalid_id"]
            ):
                raise TaskStoppedError() from None
            else:
                raise

    async def safe_edit(self, msg: str) -> None:
        """安全编辑状态消息，若编辑失败则降级为回复新消息"""
        if await self.is_deleted():
            raise TaskStoppedError()

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
        """安全发送草稿，失败时静默返回 False"""
        try:
            return await self.bot.send_message_draft(
                chat_id=self.chat_id, draft_id=self.draft_id, text=text
            )
        except Exception:
            return False


# ==================== 2. 异步安全任务队列 ====================
class TaskQueue:
    """异步安全的任务队列，用于管理待处理的 Telegram 消息任务"""

    def __init__(self):
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
