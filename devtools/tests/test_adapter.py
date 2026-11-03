# devtools/tests/test_adapter.py
"""Telegram 适配器启停测试

- start 落到 dispatcher.start_polling(bot)
- stop 落到 dispatcher.stop_polling 协程
- close 落到会话的 close 协程
- is_link_failure 转调会话那套异常族
"""

import asyncio
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from adapters.telegram.adapter import TelegramAdapter  # noqa: E402


class _FakeDispatcher:
    def __init__(self) -> None:
        self.polling_started = asyncio.Event()
        self.polling_stopped = asyncio.Event()

    async def start_polling(self, *bots: object) -> None:
        self.polling_started.set()

    async def stop_polling(self) -> None:
        self.polling_stopped.set()


class TestAdapterLifecycle(unittest.IsolatedAsyncioTestCase):
    """启停转调"""

    async def asyncSetUp(self) -> None:
        self.adapter = TelegramAdapter(token="123456:ABCdef")
        self.dispatcher = _FakeDispatcher()
        self.adapter._dispatcher = self.dispatcher  # type: ignore[assignment]

    async def test_start_polls_own_bot(self) -> None:
        await self.adapter.start()
        self.assertTrue(self.dispatcher.polling_started.is_set())

    async def test_stop_awaits_stop_polling(self) -> None:
        await self.adapter.stop()
        self.assertTrue(self.dispatcher.polling_stopped.is_set())

    async def test_platform_and_interaction_wired(self) -> None:
        self.assertEqual(self.adapter.platform, "tg")
        self.assertIs(self.adapter.interaction._bot, self.adapter._bot)

    async def test_close_releases_session(self) -> None:
        """释放连接转调会话的 close 协程"""
        closed = asyncio.Event()

        class _FakeSession:
            async def close(self) -> None:
                closed.set()

        self.adapter._bot = SimpleNamespace(session=_FakeSession())  # type: ignore[assignment]
        await self.adapter.close()
        self.assertTrue(closed.is_set())

    async def test_link_failure_uses_session_rules(self) -> None:
        """链路判定转调会话那套异常族"""
        self.assertTrue(self.adapter.is_link_failure(OSError("断了")))
        self.assertFalse(self.adapter.is_link_failure(ValueError("配置坏了")))


if __name__ == "__main__":
    unittest.main()
