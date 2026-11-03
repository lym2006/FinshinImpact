# src/adapters/telegram/adapter.py
"""Telegram 适配器

- 持有 Bot 与 Dispatcher 并托管启停
"""

from typing import TYPE_CHECKING

from core.contracts import BaseAdapter, InteractionPort
from core.domain import Platform

from ._interaction import TelegramInteractionPort
from ._normalize import NormalizeMiddleware
from .session import SSLUnverifiedSession
from .session import is_link_failure as _is_link_failure

if TYPE_CHECKING:
    from aiogram import Dispatcher


class TelegramAdapter(BaseAdapter):
    """Telegram 适配器

    - dispatcher 供装配层挂日志与注册路由
    """

    def __init__(self, token: str, *, proxy: str | None = None) -> None:
        from aiogram import Bot, Dispatcher

        self._bot = Bot(token=token, session=SSLUnverifiedSession(proxy=proxy))
        self._dispatcher = Dispatcher()
        self._interaction = TelegramInteractionPort(self._bot)
        self._normalizer = NormalizeMiddleware(self._interaction, self._bot)
        self._dispatcher.update.outer_middleware(self._normalizer)

    @property
    def platform(self) -> Platform:
        """平台标识"""
        return Platform.TELEGRAM

    @property
    def interaction(self) -> InteractionPort:
        """交互端口"""
        return self._interaction

    @property
    def dispatcher(self) -> "Dispatcher":
        """事件分发器"""
        return self._dispatcher

    async def start(self) -> None:
        """启动事件接收"""
        await self._dispatcher.start_polling(self._bot)

    async def stop(self) -> None:
        """停止事件接收

        - 轮询停了再弃在途相册，放行链不带进下次启动
        """
        await self._dispatcher.stop_polling()
        self._normalizer.drop_albums()

    async def close(self) -> None:
        """释放会话连接"""
        await self._bot.session.close()

    def is_link_failure(self, exc: BaseException) -> bool:
        """判定异常属不属于链路故障"""
        return _is_link_failure(exc)
