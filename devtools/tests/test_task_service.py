# devtools/tests/test_task_service.py
"""任务排队与调度测试

- 同容器按优先级与到达序逐条派发
- 队空即退并放掉该容器的活跃标记
- 单项报错与缺处理函数都不打死整串
- 并发闸跨容器生效，闸为一时同一时刻只跑一条
- 同类型重复交处理函数只认最先那个
- 收尾作废全部排队与在途
- 派发推进的三处逐条记账，报错项按失败记
"""

import asyncio
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from finshin_sdk import HandlerContext, InteractionPort  # noqa: E402
from finshin_sdk.domain import (  # noqa: E402
    ChatScope,
    Platform,
    TaskHandler,
)
from finshin_sdk.domain.ids import (  # noqa: E402
    KEY_SEP,
    ContainerKey,
    MessageId,
    SessionKey,
    UserId,
)
from finshin_sdk.dto import (  # noqa: E402
    ContentDTO,
    InboundEventDTO,
    MsgReferenceDTO,
    OutboundPayloadDTO,
    PrincipalDTO,
)
from services.tasks._queue import TaskItem  # noqa: E402
from services.tasks._service import TaskService  # noqa: E402

_GROUP_CONTAINER = ContainerKey("g100123")
_OTHER_CONTAINER = ContainerKey("g999")


class _NullPort(InteractionPort):
    """派发路径用的占位端口"""

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


class _StubLedger:
    """记账路径用的占位账本，只留下调用序列"""

    def __init__(self) -> None:
        self.calls: list[str] = []

    async def enqueue(self, item: TaskItem) -> None:
        self.calls.append("enqueue")

    async def begin(self, item: TaskItem) -> None:
        self.calls.append("begin")

    async def settle(self, item: TaskItem, *, failed: bool) -> None:
        self.calls.append("settle:failed" if failed else "settle:ok")

    def reset(self) -> None:
        self.calls.append("reset")


def _item(
    user: str,
    container: ContainerKey = _GROUP_CONTAINER,
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
        kind="demo.chat",
        ctx=HandlerContext(event=event, interaction=_NullPort()),
    )


class TestTaskService(unittest.IsolatedAsyncioTestCase):
    """容器级排队与派发"""

    async def asyncSetUp(self) -> None:
        self.faults: list[tuple[TaskItem, Exception]] = []
        self.ledger = _StubLedger()

    def _service(self, handlers: dict[str, object], **kwargs: int) -> TaskService:
        """把类型到处理函数的映射交进服务，报错全部收进本用例"""
        declared = [
            TaskHandler(kind=kind, run=run)  # type: ignore[arg-type]
            for kind, run in handlers.items()
        ]
        return TaskService(
            declared,
            ledger=self.ledger,
            on_fault=lambda item, e: self.faults.append((item, e)),
            **kwargs,
        )

    async def _finish(self, service: TaskService) -> None:
        """等所有在跑的消费协程收工"""
        await asyncio.gather(*list(service._runners.values()))

    async def test_dispatch_follows_arrival(self) -> None:
        gate = asyncio.Event()
        order: list[str] = []

        async def run(ctx: HandlerContext) -> None:
            order.append(str(ctx.event.principal.user))
            await gate.wait()

        service = self._service({"demo.chat": run})
        await service.enqueue(_item("111"))
        for _ in range(5):
            await asyncio.sleep(0)
        self.assertEqual(order, ["111"])

        await service.enqueue(_item("222"))
        await service.enqueue(_item("333"))

        gate.set()
        await self._finish(service)
        self.assertEqual(order, ["111", "222", "333"])

    async def test_runner_released_when_queue_drains(self) -> None:
        async def run(ctx: HandlerContext) -> None:
            return None

        service = self._service({"demo.chat": run})
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

        service = self._service({"demo.chat": run})
        await service.enqueue(_item("111"))
        await service.enqueue(_item("222"))
        await self._finish(service)

        self.assertEqual(len(self.faults), 1)
        self.assertEqual(order, ["222"])
        self.assertEqual(
            self.ledger.calls,
            ["enqueue", "enqueue", "begin", "settle:failed", "begin", "settle:ok"],
        )

    async def test_missing_handler_reports_and_moves_on(self) -> None:
        service = self._service({})
        await service.enqueue(_item("111"))
        await self._finish(service)

        self.assertIsInstance(self.faults[0][1], LookupError)
        self.assertEqual(service._runners, {})
        self.assertEqual(self.ledger.calls, ["enqueue", "settle:failed"])

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

        service = self._service({"demo.chat": run}, max_concurrency=1)
        await service.enqueue(_item("111"))
        await service.enqueue(_item("222", container=_OTHER_CONTAINER))
        await self._finish(service)

        self.assertEqual(peak, 1)
        self.assertEqual(sorted(done), ["111", "222"])

    async def test_new_item_restarts_finished_runner(self) -> None:
        order: list[str] = []

        async def run(ctx: HandlerContext) -> None:
            order.append(str(ctx.event.principal.user))

        service = self._service({"demo.chat": run})
        await service.enqueue(_item("111"))
        await self._finish(service)
        await service.enqueue(_item("222"))
        await self._finish(service)

        self.assertEqual(order, ["111", "222"])

    async def test_same_kind_keeps_first_handler(self) -> None:
        order: list[str] = []

        async def first(ctx: HandlerContext) -> None:
            order.append("first")

        async def second(ctx: HandlerContext) -> None:
            order.append("second")

        service = TaskService(
            [
                TaskHandler(kind="demo.chat", run=first),
                TaskHandler(kind="demo.chat", run=second),
            ],
            ledger=self.ledger,
            on_fault=lambda item, e: self.faults.append((item, e)),
        )
        await service.enqueue(_item("111"))
        await self._finish(service)

        self.assertEqual(order, ["first"])

    async def test_release_drops_rows_and_runners(self) -> None:
        gate = asyncio.Event()
        order: list[str] = []

        async def run(ctx: HandlerContext) -> None:
            order.append(str(ctx.event.principal.user))
            await gate.wait()

        service = self._service({"demo.chat": run})
        await service.enqueue(_item("111"))
        for _ in range(5):
            await asyncio.sleep(0)
        await service.enqueue(_item("222"))
        await service.enqueue(_item("333", container=_OTHER_CONTAINER))

        await service.release()

        self.assertEqual(service._runners, {})
        self.assertEqual(service.size(_item("111").container_key), 0)
        self.assertEqual(order, ["111"])
        self.assertEqual(self.faults, [])
        self.assertIn("reset", self.ledger.calls)

    async def test_enqueue_after_release_starts_new_runner(self) -> None:
        order: list[str] = []

        async def run(ctx: HandlerContext) -> None:
            order.append(str(ctx.event.principal.user))

        service = self._service({"demo.chat": run})
        await service.enqueue(_item("111"))
        await self._finish(service)
        await service.enqueue(_item("222"))
        await service.release()
        self.assertEqual(order, ["111"])

        await service.enqueue(_item("333"))
        await self._finish(service)

        self.assertEqual(order, ["111", "333"])


if __name__ == "__main__":
    unittest.main()
