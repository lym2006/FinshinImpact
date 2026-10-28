# src/adapters/telegram/_album.py
"""相册缓冲

- 同组同人的多条更新并成一条放行，满额即放，其余等下一次派发
- 放行沿末条更新的事件链走，整组只点一次下游
"""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from aiogram.types import Message, TelegramObject

from core.domain.ids import ChatId, MediaGroupId, UserId
from utils import get_logger

from ._fields import sender_id

_logger = get_logger("Adapter")

# 分发器交下的事件链入口
UpdateHandler = Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]]

# 缓冲键：会话、组标识、发言人
_AlbumKey = tuple[ChatId, MediaGroupId, UserId]


def _key_of(raw: Message) -> _AlbumKey:
    """按会话、组标识与发言人取缓冲键"""
    return (
        ChatId(str(raw.chat.id)),
        MediaGroupId(str(raw.media_group_id)),
        sender_id(raw),
    )


@dataclass(slots=True)
class AlbumBatch:
    """一组攒齐的相册更新

    - handler、event 与 data 取末条，整组只放一次行
    """

    items: list[Message]
    handler: UpdateHandler
    event: TelegramObject
    data: dict[str, Any]


@dataclass(slots=True)
class _Pending:
    """在途分组

    - 条目逐条并入，收口时整组一次放行
    """

    items: list[Message]
    handler: UpdateHandler
    event: TelegramObject
    data: dict[str, Any]


class AlbumCollector:
    """相册收集器

    - 只接带组标识的更新，其余由调用方照常放行
    """

    def __init__(
        self,
        on_flush: Callable[[AlbumBatch], Awaitable[None]],
    ) -> None:
        self._on_flush = on_flush
        self._pending: dict[_AlbumKey, _Pending] = {}

    async def collect(
        self,
        raw: Message,
        handler: UpdateHandler,
        event: TelegramObject,
        data: dict[str, Any],
    ) -> None:
        """收一条相册更新

        - 组内首条挂收口，同批其余条目并进同一束
        """
        key = _key_of(raw)
        pending = self._pending.get(key)
        if pending is None:
            pending = _Pending(items=[raw], handler=handler, event=event, data=data)
            self._pending[key] = pending
        else:
            pending.items.append(raw)
            pending.handler = handler
            pending.event = event
            pending.data = data

        self._schedule(key)

    def drop(self) -> None:
        """丢弃在途分组，停服收尾用"""
        self._pending.clear()

    def _schedule(self, key: _AlbumKey) -> None:
        """挂一次派发后的收口，取走即出表防重复投递"""
        asyncio.get_running_loop().call_soon(
            lambda: asyncio.ensure_future(self._flush(key))
        )

    async def _flush(self, key: _AlbumKey) -> None:
        """放行整组"""
        pending = self._pending.pop(key, None)
        if pending is None:
            return
        batch = AlbumBatch(
            items=pending.items,
            handler=pending.handler,
            event=pending.event,
            data=pending.data,
        )
        try:
            await self._on_flush(batch)
        except Exception as e:  # 放行链上的异常已脱离分发器，此处兜住不外溢
            _logger.send_error("相册放行失败", e)
