# devtools/tests/test_album_collector.py
"""相册缓冲样例测试

- 同组条目一次派发并成一条放行，同组不同发言人各攒各的
- 放行取末条更新的事件链，弃组后不放行
"""

import asyncio
import sys
import unittest
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from aiogram.types import Chat, Message, PhotoSize, Update, User  # noqa: E402

from adapters.telegram._album import AlbumBatch, AlbumCollector  # noqa: E402

_CHAT = Chat(id=-100123, type="supergroup", title="测试群")
_USER = User(id=456, is_bot=False, first_name="三", last_name="张")
_OTHER = User(id=999, is_bot=False, first_name="四", last_name="李")
_PHOTO = PhotoSize(file_id="p", file_unique_id="u", width=1, height=1)


def _message(message_id: int, group: str, sender: User = _USER) -> Message:
    """构造一条相册内消息"""
    return Message(
        message_id=message_id,
        date=datetime(2026, 10, 16, 12, 0),
        chat=_CHAT,
        from_user=sender,
        photo=[_PHOTO],
        media_group_id=group,
    )


async def _noop_handler(event: Any, data: dict[str, Any]) -> str:
    return "passed"


class _Sink:
    """放行收口"""

    def __init__(self) -> None:
        self.batches: list[AlbumBatch] = []

    async def on_flush(self, batch: AlbumBatch) -> None:
        self.batches.append(batch)


async def _collect(collector: AlbumCollector, message: Message) -> None:
    """以该消息为末条走一次收集"""
    await collector.collect(
        message,
        _noop_handler,
        Update(update_id=1, message=message),
        {},
    )


async def _dispatch_pass() -> None:
    """走完一轮派发

    - 已排队的其余条目任务先跑完，收口回调排在它们之后，整组才并成一条
    - 再多让两轮，收口起的协程跑到放行结束
    """
    for _ in range(3):
        await asyncio.sleep(0)


class TestAlbumCollector(unittest.IsolatedAsyncioTestCase):
    """一次派发收口与弃组"""

    def _collector(self, sink: _Sink) -> AlbumCollector:
        return AlbumCollector(sink.on_flush)

    async def test_dispatch_flushes_whole_group(self) -> None:
        """一轮派发把整组放行一次"""
        sink = _Sink()
        collector = self._collector(sink)
        for message_id in (10, 11):
            await _collect(collector, _message(message_id, "g1"))
        self.assertEqual(sink.batches, [])

        await _dispatch_pass()
        self.assertEqual([len(b.items) for b in sink.batches], [2])
        self.assertEqual([m.message_id for m in sink.batches[0].items], [10, 11])

    async def test_other_sender_keeps_separate(self) -> None:
        """同组不同发言人不成一束"""
        sink = _Sink()
        collector = self._collector(sink)
        await _collect(collector, _message(10, "g1", _USER))
        await _collect(collector, _message(11, "g1", _OTHER))

        await _dispatch_pass()
        self.assertEqual([len(b.items) for b in sink.batches], [1, 1])

    async def test_flush_carries_last_event(self) -> None:
        """放行用末条更新的事件链"""
        sink = _Sink()
        collector = self._collector(sink)
        await _collect(collector, _message(10, "g1"))
        last = _message(11, "g1")
        await _collect(collector, last)

        await _dispatch_pass()
        batch = sink.batches[0]
        self.assertEqual(len(batch.items), 2)
        self.assertEqual(batch.event.message.message_id, 11)  # type: ignore[union-attr]
        self.assertIs(batch.handler, _noop_handler)

    async def test_drop_before_dispatch(self) -> None:
        """弃组后派发不放行"""
        sink = _Sink()
        collector = self._collector(sink)
        await _collect(collector, _message(10, "g1"))
        collector.drop()
        self.assertEqual(collector._pending, {})

        await _dispatch_pass()
        self.assertEqual(sink.batches, [])

    async def test_group_restarts_after_flush(self) -> None:
        """放行后同键再起新组不并旧条"""
        sink = _Sink()
        collector = self._collector(sink)
        await _collect(collector, _message(10, "g1"))
        await _dispatch_pass()
        await _collect(collector, _message(11, "g1"))
        await _dispatch_pass()

        self.assertEqual([len(b.items) for b in sink.batches], [1, 1])


if __name__ == "__main__":
    unittest.main()
