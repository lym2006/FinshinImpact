# src/adapters/telegram/_normalize.py
"""入站事件归一化中间件

- 归一成功即向 data 写入 ctx 一个键
- 相册条先攒进缓冲，整组到点只走一次事件链
"""

from typing import Any

from aiogram import BaseMiddleware, Bot
from aiogram.types import TelegramObject, Update

from core.contracts import InteractionPort
from core.domain.ids import UserId
from services.context import HandlerContext
from utils import get_logger

from ._album import AlbumBatch, AlbumCollector, UpdateHandler
from ._event import BotIdentity, normalize_album, normalize_update

_logger = get_logger("Adapter")


class NormalizeMiddleware(BaseMiddleware):
    """归一化中间件

    - 归一成功即向 data 写入 ctx 一个键
    - 相册条先攒进缓冲，整组到点只走一次事件链
    """

    def __init__(self, interaction: InteractionPort, bot: Bot) -> None:
        super().__init__()
        self._interaction = interaction
        self._bot = bot
        self._albums = AlbumCollector(self._flush_album)

    def drop_albums(self) -> None:
        """丢弃在途相册

        - 停服收尾调用，在途分组不带进下次启动
        """
        self._albums.drop()

    async def __call__(
        self,
        handler: UpdateHandler,
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """归一并放行"""
        if isinstance(event, Update) and event.message is not None:
            message = event.message
            try:
                identity = await self._identity()
                if message.media_group_id is None:
                    inbound = normalize_update(event, identity=identity)
                else:
                    await self._albums.collect(message, handler, event, data)
                    return None
            except Exception as e:
                # 单条畸形更新只记日志，不能中断事件流
                _logger.send_error("事件归一失败", e)
                inbound = None
            if inbound is not None:
                data["ctx"] = HandlerContext(
                    event=inbound,
                    interaction=self._interaction,
                )

        return await handler(event, data)

    async def _identity(self) -> BotIdentity:
        """取本机器人标识作点名与引用归属的基准"""
        me = await self._bot.me()
        return BotIdentity(user_id=UserId(str(me.id)), username=me.username or "")

    async def _flush_album(self, batch: AlbumBatch) -> None:
        """整组并成一条归一事件后沿末条的事件链放行"""
        inbound = normalize_album(batch.items, identity=await self._identity())
        if inbound is not None:
            batch.data["ctx"] = HandlerContext(
                event=inbound,
                interaction=self._interaction,
            )
        await batch.handler(batch.event, batch.data)
