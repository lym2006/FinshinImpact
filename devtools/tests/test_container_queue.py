# devtools/tests/test_container_queue.py
"""容器级排队接线测试

- 同群两名成员共用一串会话键
- 不同容器各占一串
- 入队走任务服务，同串第二条排在本条之后
- 停服收尾清空排队与在途压缩
"""

import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from bundled.AI.core import active_tasks  # noqa: E402
from bundled.AI.services import _ai_chat, _cleanup  # noqa: E402
from bundled.AI.utils import make_session_key  # noqa: E402
from finshin_sdk.domain import ChatScope, Platform, TaskHandler  # noqa: E402
from finshin_sdk.domain.ids import (  # noqa: E402
    ContainerKey,
    MessageId,
    SessionKey,
    UserId,
)
from finshin_sdk.dto import (  # noqa: E402
    ContentDTO,
    InboundEventDTO,
    MsgReferenceDTO,
    PrincipalDTO,
)
from services.tasks import configure_task_service, get_task_service  # noqa: E402

_GROUP_KEY = SessionKey("tg.g100123")


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


class _StubLedger:
    """接线测试用的占位账本，只留调用序列不碰库"""

    def __init__(self) -> None:
        self.calls: list[str] = []

    async def enqueue(self, item: object) -> None:
        self.calls.append("enqueue")

    async def begin(self, item: object) -> None:
        self.calls.append("begin")

    async def settle(self, item: object, *, failed: bool) -> None:
        self.calls.append("settle:failed" if failed else "settle:ok")

    def reset(self) -> None:
        self.calls.append("reset")


async def _enqueue(*, ctx: _Ctx) -> None:
    """走过对话入口的入队处理"""
    await _ai_chat.handle_ai_chat(ctx)


async def _no_purge(*_args: object) -> int:
    """清理路径打桩，返回值恒为零"""
    return 0


async def _hold(ctx: _Ctx) -> None:
    """占位处理：一直等到被取消"""
    await asyncio.sleep(30)


def _key(user: str, scope: ChatScope) -> SessionKey:
    """按事件取这条消息落进哪一串"""
    return make_session_key(_event(user, scope).principal)


class TestContainerKeying(unittest.TestCase):
    """会话键按容器分串"""

    def test_group_members_share_one_key(self) -> None:
        """同群两名成员落进同一串"""
        self.assertEqual(
            {_key("111", ChatScope.GROUP), _key("222", ChatScope.GROUP)}, {_GROUP_KEY}
        )

    def test_private_chats_split_by_container(self) -> None:
        """两名私聊各占一串"""
        self.assertEqual(
            sorted([_key("111", ChatScope.PRIVATE), _key("222", ChatScope.PRIVATE)]),
            [SessionKey("tg.u111"), SessionKey("tg.u222")],
        )


class TestEnqueueThroughService(unittest.TestCase):
    """对话入队交给任务服务"""

    def test_second_group_message_waits_behind_the_first(self) -> None:
        """同群第二条排在第一条之后，第一条答完才轮到它"""
        started = asyncio.Event()
        gate = asyncio.Event()
        finished = asyncio.Event()
        order: list[str] = []

        async def run(ctx: _Ctx) -> None:
            order.append(str(ctx.event.principal.user))
            started.set()
            await gate.wait()
            if len(order) == 2:
                finished.set()

        async def _fault(item: object, error: Exception) -> None:
            raise AssertionError(f"派发不该报错：{error}")

        async def _run() -> int:
            configure_task_service(
                [TaskHandler(kind="AI.chat", run=run)],
                ledger=_StubLedger(),
                on_fault=_fault,
            )
            await _enqueue(ctx=_Ctx(_event("111", ChatScope.GROUP)))
            await started.wait()
            await _enqueue(ctx=_Ctx(_event("222", ChatScope.GROUP)))

            queued = get_task_service().size(_GROUP_KEY)
            gate.set()
            await asyncio.wait_for(finished.wait(), timeout=1)
            return queued

        try:
            queued = asyncio.run(_run())
        finally:
            configure_task_service([], ledger=_StubLedger(), on_fault=_fault)

        self.assertEqual(queued, 1)
        self.assertEqual(order, ["111", "222"])


class TestShutdownRelease(unittest.TestCase):
    """停服收尾"""

    def setUp(self) -> None:
        active_tasks.clear()

    def test_teardown_clears_queue_and_cancels_inflight(self) -> None:
        """收尾清空排队，在途压缩收到取消"""
        box: dict[str, asyncio.Task] = {}
        ledger = _StubLedger()

        async def _fault(item: object, error: Exception) -> None:
            raise AssertionError(f"派发不该报错：{error}")

        async def _run() -> int:
            configure_task_service(
                [TaskHandler(kind="AI.chat", run=_hold)],
                ledger=ledger,
                on_fault=_fault,
            )
            await _enqueue(ctx=_Ctx(_event("111", ChatScope.GROUP)))
            await _enqueue(ctx=_Ctx(_event("222", ChatScope.GROUP)))

            inflight = asyncio.create_task(asyncio.sleep(30))
            active_tasks.add(inflight)
            box["inflight"] = inflight

            cleaner = asyncio.create_task(_cleanup.cleanup_loop())
            await asyncio.sleep(0)
            cleaner.cancel()
            await asyncio.gather(cleaner, return_exceptions=True)

            return get_task_service().size(_GROUP_KEY)

        with (
            patch.object(_cleanup, "_purge_records", lambda _deadline: ()),
            patch.object(_cleanup, "purge_sessions", _no_purge),
            patch.object(_cleanup, "purge_idle_sessions", _no_purge),
        ):
            queued = asyncio.run(_run())
        configure_task_service([], ledger=_StubLedger(), on_fault=_fault)

        self.assertEqual(queued, 0)
        self.assertEqual(active_tasks, set())
        self.assertTrue(box["inflight"].cancelled())
        # 在途那条被取消即不写终态，库里留着活行等下次启动交代
        self.assertEqual(ledger.calls, ["enqueue", "enqueue", "begin", "reset"])


if __name__ == "__main__":
    unittest.main()
