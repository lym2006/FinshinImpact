# devtools/tests/test_task_service.py
"""任务排队与调度测试

- 同容器按优先级与到达序逐条派发
- 队空即退并放掉该容器的活跃标记
- 单项报错与缺处理函数都不打死整串
- 并发闸跨容器生效，闸为一时同一时刻只跑一条
"""

import asyncio
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from core.contracts import InteractionPort  # noqa: E402
from core.domain import ChatScope, Platform, TaskKind, TaskPriority  # noqa: E402
from core.domain.ids import (  # noqa: E402
    KEY_SEP,
    ContainerKey,
    MessageId,
    SessionKey,
    UserId,
)
from core.dto import (  # noqa: E402
    ContentDTO,
    InboundEventDTO,
    MsgReferenceDTO,
    OutboundPayloadDTO,
    PrincipalDTO,
)
from services.context import HandlerContext  # noqa: E402
from services.tasks._queue import TaskItem  # noqa: E402
from services.tasks._service import TaskService  # noqa: E402

_GROUP_CONTAINER = ContainerKey("g100123")
_OTHER_CONTAINER = ContainerKey("g999")


class _NullPort(InteractionPort):
    """占位端口，派发不碰它"""

    async def send_message(
        self,
        principal: PrincipalDTO,
        content: OutboundPayloadDTO,
        *,
        mention: bool = False,
        reply_ref: MsgReferenceDTO | None = None,
    ) -> MsgReferenceDTO | None:
        return None

    async def probe_existence(self, target: MsgReferenceDTO) -> bool:
        return True

    def mention_fragment(self, principal: PrincipalDTO) -> str:
        return "@张三"


def _item(
    user: str,
    container: ContainerKey = _GROUP_CONTAINER,
    kind: TaskKind = TaskKind.CHAT,
    priority: TaskPriority = TaskPriority.NORMAL,
) -> TaskItem:
    """构造一条排队项"""
    principal = PrincipalDTO(
        platform=Platform.TELEGRAM, container=container, user=UserId(user)
    )
    ref = MsgReferenceDTO(
        platform=Platform.TELEGRAM, container=container, message_id=MessageId("7")
    )
    event = InboundEventDTO(
        ref=ref,
        principal=principal,
        content=ContentDTO(text="说一句"),
        scope=ChatScope.GROUP,
    )
    return TaskItem(
        container_key=SessionKey(f"{principal.platform}{KEY_SEP}{container}"),
        principal_key=principal.key,
        kind=kind,
        priority=priority,
        ctx=HandlerContext(event=event, interaction=_NullPort()),
    )


class TestTaskService(unittest.IsolatedAsyncioTestCase):
    """容器级排队与派发"""

    async def asyncSetUp(self) -> None:
        self.faults: list[tuple[TaskItem, Exception]] = []

    def _service(self, handlers: dict[TaskKind, object], **kwargs: int) -> TaskService:
        """装配一只服务，报错全部收进本用例"""
        return TaskService(
            handlers, on_fault=lambda item, e: self.faults.append((item, e)), **kwargs
        )

    async def _finish(self, service: TaskService) -> None:
        """等所有在跑的消费协程收工"""
        await asyncio.gather(*list(service._runners.values()))

    async def test_dispatch_follows_priority(self) -> None:
        gate = asyncio.Event()
        order: list[str] = []

        async def run(ctx: HandlerContext) -> None:
            order.append(str(ctx.event.principal.user))
            await gate.wait()

        service = self._service({TaskKind.CHAT: run})
        await service.enqueue(_item("111"))
        for _ in range(5):
            await asyncio.sleep(0)
        self.assertEqual(order, ["111"])

        await service.enqueue(_item("222", priority=TaskPriority.HIGH))
        await service.enqueue(_item("333", priority=TaskPriority.IMMEDIATE))

        gate.set()
        await self._finish(service)
        self.assertEqual(order, ["111", "333", "222"])

    async def test_runner_released_when_queue_drains(self) -> None:
        async def run(ctx: HandlerContext) -> None:
            return None

        service = self._service({TaskKind.CHAT: run})
        await service.enqueue(_item("111"))
        await self._finish(service)

        self.assertEqual(service._runners, {})

    async def test_fault_does_not_stop_the_rest(self) -> None:
        order: list[str] = []

        async def run(ctx: HandlerContext) -> None:
            user = str(ctx.event.principal.user)
            if user == "111":
                raise RuntimeError("炸了")
            order.append(user)

        service = self._service({TaskKind.CHAT: run})
        await service.enqueue(_item("111"))
        await service.enqueue(_item("222"))
        await self._finish(service)

        self.assertEqual(len(self.faults), 1)
        self.assertEqual(order, ["222"])

    async def test_missing_handler_reports_and_moves_on(self) -> None:
        service = self._service({})
        await service.enqueue(_item("111", kind=TaskKind.HISTORY))
        await self._finish(service)

        self.assertIsInstance(self.faults[0][1], LookupError)
        self.assertEqual(service._runners, {})

    async def test_gate_serializes_across_containers(self) -> None:
        inflight = 0
        peak = 0
        done: list[str] = []

        async def run(ctx: HandlerContext) -> None:
            nonlocal inflight, peak
            inflight += 1
            peak = max(peak, inflight)
            await asyncio.sleep(0.01)
            inflight -= 1
            done.append(str(ctx.event.principal.user))

        service = self._service({TaskKind.CHAT: run}, max_concurrency=1)
        await service.enqueue(_item("111"))
        await service.enqueue(_item("222", container=_OTHER_CONTAINER))
        await self._finish(service)

        self.assertEqual(peak, 1)
        self.assertEqual(sorted(done), ["111", "222"])

    async def test_new_item_restarts_finished_runner(self) -> None:
        order: list[str] = []

        async def run(ctx: HandlerContext) -> None:
            order.append(str(ctx.event.principal.user))

        service = self._service({TaskKind.CHAT: run})
        await service.enqueue(_item("111"))
        await self._finish(service)
        await service.enqueue(_item("222"))
        await self._finish(service)

        self.assertEqual(order, ["111", "222"])


if __name__ == "__main__":
    unittest.main()
