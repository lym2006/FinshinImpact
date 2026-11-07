# devtools/tests/test_hot_queue.py
"""热队列测试

- 入队按容器到达序补号
- 出队按优先级与到达序取最靠前的一条
- 同容器两名成员排一串，不同容器互不影响
- 串排空即释放该容器的键与到达序计数
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from core.domain import ChatScope, Platform, TaskKind  # noqa: E402
from core.domain.ids import (  # noqa: E402
    KEY_SEP,
    ContainerKey,
    MessageId,
    PrincipalKey,
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
from finshin_sdk import InteractionPort  # noqa: E402
from services.context import HandlerContext  # noqa: E402
from services.tasks._queue import HotQueue, TaskItem  # noqa: E402

_GROUP = SessionKey(f"tg{KEY_SEP}g100123")
_GROUP_CONTAINER = ContainerKey("g100123")
_OTHER = SessionKey(f"tg{KEY_SEP}g999")
_OTHER_CONTAINER = ContainerKey("g999")


class _NullPort(InteractionPort):
    """入队路径用的占位端口"""

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


def _ctx(user: str, container: ContainerKey = _GROUP_CONTAINER) -> HandlerContext:
    """构造一条入站事件的处理上下文"""
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
        scope=ChatScope.GROUP if container.startswith("g") else ChatScope.PRIVATE,
    )
    return HandlerContext(event=event, interaction=_NullPort())


def _item(
    user: str,
    container: ContainerKey = _GROUP_CONTAINER,
) -> TaskItem:
    """构造一条排队项，序号交给队列补"""
    ctx = _ctx(user, container)
    return TaskItem(
        container_key=SessionKey(f"{ctx.event.principal.platform}{KEY_SEP}{container}"),
        principal_key=ctx.event.principal.key,
        kind=TaskKind.CHAT,
        ctx=ctx,
    )


class TestHotQueue(unittest.IsolatedAsyncioTestCase):
    """容器级排队"""

    async def asyncSetUp(self) -> None:
        self.queue = HotQueue()

    async def test_push_numbers_by_arrival(self) -> None:
        first = await self.queue.push(_item("111"))
        second = await self.queue.push(_item("222"))

        self.assertEqual((first.sequence, second.sequence), (0, 1))
        self.assertEqual(self.queue.size(_GROUP), 2)

    async def test_pop_takes_arrival_order(self) -> None:
        await self.queue.push(_item("111"))
        await self.queue.push(_item("222"))
        await self.queue.push(_item("333"))

        self.assertEqual(
            (await self.queue.pop_next(_GROUP)).principal_key,
            PrincipalKey("tg.g100123.111"),
        )
        self.assertEqual(
            (await self.queue.pop_next(_GROUP)).principal_key,
            PrincipalKey("tg.g100123.222"),
        )
        self.assertEqual(
            (await self.queue.pop_next(_GROUP)).principal_key,
            PrincipalKey("tg.g100123.333"),
        )

    async def test_empty_container_yields_none(self) -> None:
        self.assertIsNone(await self.queue.pop_next(_GROUP))
        self.assertEqual(self.queue.size(_GROUP), 0)

    async def test_drained_container_releases_keys(self) -> None:
        await self.queue.push(_item("111"))
        await self.queue.pop_next(_GROUP)

        self.assertEqual(self.queue._by_container, {})
        self.assertEqual(self.queue._arrived, {})

        again = await self.queue.push(_item("111"))
        self.assertEqual(again.sequence, 0)

    async def test_containers_do_not_share_rows(self) -> None:
        await self.queue.push(_item("111"))
        await self.queue.push(_item("222", container=_OTHER_CONTAINER))

        self.assertEqual(self.queue.size(_GROUP), 1)
        self.assertEqual(self.queue.size(_OTHER), 1)

    async def test_discard_all_drops_every_container(self) -> None:
        await self.queue.push(_item("111"))
        await self.queue.push(_item("222", container=_OTHER_CONTAINER))

        self.assertEqual(await self.queue.discard_all(), 2)
        self.assertEqual(self.queue.size(_GROUP), 0)
        self.assertEqual(self.queue.size(_OTHER), 0)


if __name__ == "__main__":
    unittest.main()
