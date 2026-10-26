# devtools/tests/test_container_queue.py
"""容器级排队测试

- 同群两名成员共用一串队列与一把锁
- 不同容器各占一串
- 停服收尾作废三本内存账并收掉在途协程
- 收尾后同一容器再入队能起重启新的监控循环
"""

import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from core.domain import ChatScope, Platform  # noqa: E402
from core.domain.ids import ContainerKey, MessageId, SessionKey, UserId  # noqa: E402
from core.dto import (  # noqa: E402
    ContentDTO,
    InboundEventDTO,
    MsgReferenceDTO,
    PrincipalDTO,
)
from plugins.AI.core import (  # noqa: E402
    active_tasks,
    session_guard,
    session_states,
    task_queues,
)
from plugins.AI.services import _ai_chat, _monitor  # noqa: E402
from plugins.AI.state import session_locks  # noqa: E402


def _event(user: str, scope: ChatScope) -> InboundEventDTO:
    """构造一条入站事件"""
    container = ContainerKey("g100123" if scope == ChatScope.GROUP else f"u{user}")
    principal = PrincipalDTO(
        platform=Platform.TELEGRAM, container=container, user=UserId(user)
    )
    ref = MsgReferenceDTO(
        platform=Platform.TELEGRAM, container=container, message_id=MessageId("7")
    )
    return InboundEventDTO(
        ref=ref,
        principal=principal,
        content=ContentDTO(text="说一句"),
        scope=scope,
    )


class _Ctx:
    """只带事件的假上下文"""

    def __init__(self, event: InboundEventDTO) -> None:
        self.event = event


@session_guard
async def _touch(*, ctx: _Ctx) -> None:
    """走过会话守卫的空处理"""


@session_guard
async def _enqueue(*, ctx: _Ctx) -> None:
    """走过会话守卫的入队处理"""
    await _ai_chat.handle_ai_chat(ctx)


async def _no_purge(*_args: object) -> int:
    """清理路径打桩，收尾用例不碰库与磁盘"""
    return 0


async def _busy_group() -> SessionKey:
    """造出一串正在应答中的群会话"""
    await _touch(ctx=_Ctx(_event("111", ChatScope.GROUP)))
    key = SessionKey("tg.g100123")
    session_states[key].is_active = True
    return key


class TestContainerQueue(unittest.TestCase):
    def setUp(self) -> None:
        session_states.clear()
        task_queues.clear()

    def test_group_members_share_one_queue(self) -> None:
        """同群两名成员落进同一串队列"""
        asyncio.run(_touch(ctx=_Ctx(_event("111", ChatScope.GROUP))))
        asyncio.run(_touch(ctx=_Ctx(_event("222", ChatScope.GROUP))))

        self.assertEqual(list(task_queues), [SessionKey("tg.g100123")])
        self.assertEqual(list(session_states), [SessionKey("tg.g100123")])

    def test_private_chats_split_by_container(self) -> None:
        """两名私聊各占一串"""
        asyncio.run(_touch(ctx=_Ctx(_event("111", ChatScope.PRIVATE))))
        asyncio.run(_touch(ctx=_Ctx(_event("222", ChatScope.PRIVATE))))

        self.assertEqual(
            sorted(task_queues), [SessionKey("tg.u111"), SessionKey("tg.u222")]
        )

    def test_enqueue_starts_one_monitor_per_group(self) -> None:
        """同群第二条消息并入已启动的监控循环"""
        started: list[str] = []

        async def _fake_loop(key: SessionKey) -> None:
            started.append(key)

        events = [_event("111", ChatScope.GROUP), _event("222", ChatScope.GROUP)]

        async def _run() -> None:
            for event in events:
                await _enqueue(ctx=_Ctx(event))
            await asyncio.sleep(0)

        with patch.object(_ai_chat, "monitor_loop", _fake_loop):
            asyncio.run(_run())

        self.assertEqual(started, ["tg.g100123"])
        self.assertEqual(task_queues[SessionKey("tg.g100123")].size, 2)


class TestShutdownRelease(unittest.TestCase):
    def setUp(self) -> None:
        session_states.clear()
        task_queues.clear()
        session_locks.clear()
        active_tasks.clear()

    def test_teardown_clears_memory_and_cancels_inflight(self) -> None:
        """停服收尾抹平内存态，在途协程收到取消"""
        key = asyncio.run(_busy_group())
        session_locks[key]
        box: dict[str, asyncio.Task] = {}

        async def _run() -> None:
            inflight = asyncio.create_task(asyncio.sleep(30))
            active_tasks.add(inflight)
            box["inflight"] = inflight

            cleaner = asyncio.create_task(_monitor.cleanup_loop())
            await asyncio.sleep(0)
            cleaner.cancel()
            await asyncio.gather(cleaner, return_exceptions=True)

        with (
            patch.object(_monitor, "_purge_records", lambda _deadline: ()),
            patch.object(_monitor, "purge_sessions", _no_purge),
            patch.object(_monitor, "purge_idle_sessions", _no_purge),
        ):
            asyncio.run(_run())

        self.assertEqual(session_states, {})
        self.assertEqual(task_queues, {})
        self.assertEqual(len(session_locks), 0)
        self.assertEqual(active_tasks, set())
        self.assertTrue(box["inflight"].cancelled())

    def test_monitor_restarts_after_teardown(self) -> None:
        """收尾后同串容器再入队，监控循环重新起住"""
        started: list[str] = []

        async def _fake_loop(key: SessionKey) -> None:
            started.append(key)

        async def _run() -> None:
            await _busy_group()
            cleaner = asyncio.create_task(_monitor.cleanup_loop())
            await asyncio.sleep(0)
            cleaner.cancel()
            await asyncio.gather(cleaner, return_exceptions=True)

            await _enqueue(ctx=_Ctx(_event("111", ChatScope.GROUP)))

        with (
            patch.object(_ai_chat, "monitor_loop", _fake_loop),
            patch.object(_monitor, "_purge_records", lambda _deadline: ()),
            patch.object(_monitor, "purge_sessions", _no_purge),
            patch.object(_monitor, "purge_idle_sessions", _no_purge),
        ):
            asyncio.run(_run())

        self.assertEqual(started, ["tg.g100123"])


if __name__ == "__main__":
    unittest.main()
