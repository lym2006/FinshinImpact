# src/adapters/telegram/adapter.py
"""Telegram 适配器

- 持有 Bot 与 Dispatcher 并托管启停
"""

from typing import TYPE_CHECKING

from core.contracts import BaseAdapter, InteractionPort
from core.domain import Platform

from ._interaction import TelegramInteractionPort
from ._normalize import NormalizeMiddleware

if TYPE_CHECKING:
    from aiogram import Bot, Dispatcher


class TelegramAdapter(BaseAdapter):
    """Telegram 适配器

    - bot 与 dispatcher 供装配层挂日志与注册路由
    """

    def __init__(self, token: str, *, proxy: str | None = None) -> None:
        from aiogram import Bot, Dispatcher

        from .session import SSLUnverifiedSession

        self._bot = Bot(token=token, session=SSLUnverifiedSession(proxy=proxy))
        self._dispatcher = Dispatcher()
        self._interaction = TelegramInteractionPort(self._bot)
        self._dispatcher.update.outer_middleware(
            NormalizeMiddleware(self._interaction, self._bot)
        )

    @property
    def platform(self) -> Platform:
        """平台标识"""
        return Platform.TELEGRAM

    @property
    def interaction(self) -> InteractionPort:
        """交互端口"""
        return self._interaction

    @property
    def bot(self) -> "Bot":
        """Telegram 客户端"""
        return self._bot

    @property
    def dispatcher(self) -> "Dispatcher":
        """事件分发器"""
        return self._dispatcher

    async def start(self) -> None:
        """启动事件接收"""
        await self._dispatcher.start_polling(self._bot)

    async def stop(self) -> None:
        """停止并释放连接"""
        await self._dispatcher.stop_polling()
