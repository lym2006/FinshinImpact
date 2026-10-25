# devtools/tests/test_context.py
"""处理上下文样例测试

- 文字入参自动包成外发负载
- reply 带当前事件引用，answer 不带
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from core.contracts import InteractionPort  # noqa: E402
from core.domain import ChatScope, ContentKind, Platform  # noqa: E402
from core.domain.ids import ContainerKey, MessageId, UserId  # noqa: E402
from core.dto import (  # noqa: E402
    ContentDTO,
    InboundEventDTO,
    MsgReferenceDTO,
    OutboundPayloadDTO,
    PrincipalDTO,
)
from services.context import HandlerContext  # noqa: E402


def _event() -> InboundEventDTO:
    """构造一条私聊文字事件"""
    container = ContainerKey("u456")
    principal = PrincipalDTO(
        platform=Platform.TELEGRAM, container=container, user=UserId("456")
    )
    ref = MsgReferenceDTO(
        platform=Platform.TELEGRAM, container=container, message_id=MessageId("7")
    )
    return InboundEventDTO(
        ref=ref,
        principal=principal,
        content=ContentDTO(text="你好"),
        scope=ChatScope.PRIVATE,
    )


class _Call(dict):
    """一次端口调用"""


class _RecordingPort(InteractionPort):
    """记录入参的假端口"""

    def __init__(self) -> None:
        self.calls: list[_Call] = []
        self.mentions: list[PrincipalDTO] = []

    async def send_message(
        self,
        principal: PrincipalDTO,
        content: OutboundPayloadDTO,
        *,
        mention: bool = False,
        reply_ref: MsgReferenceDTO | None = None,
    ) -> MsgReferenceDTO | None:
        self.calls.append(_Call(content=content, mention=mention, reply_ref=reply_ref))
        return None

    async def probe_existence(self, target: MsgReferenceDTO) -> bool:
        return True

    def mention_fragment(self, principal: PrincipalDTO) -> str:
        self.mentions.append(principal)
        return "@张三"


class TestHandlerContext(unittest.IsolatedAsyncioTestCase):
    """上下文便捷方法"""

    async def asyncSetUp(self) -> None:
        self.port = _RecordingPort()
        self.ctx = HandlerContext(event=_event(), interaction=self.port)

    async def test_answer_wraps_text_as_payload(self) -> None:
        await self.ctx.answer("稍等")
        self.assertEqual(
            self.port.calls[0]["content"],
            OutboundPayloadDTO(kind=ContentKind.TEXT, text="稍等"),
        )
        self.assertIsNone(self.port.calls[0]["reply_ref"])

    async def test_reply_passes_event_ref(self) -> None:
        await self.ctx.reply("收到")
        self.assertEqual(self.port.calls[0]["reply_ref"], self.ctx.event.ref)

    async def test_payload_passed_through(self) -> None:
        payload = OutboundPayloadDTO(
            kind=ContentKind.DOCUMENT, local_path="a.md", file_name="a.md"
        )
        await self.ctx.answer(payload)
        self.assertIs(self.port.calls[0]["content"], payload)

    async def test_principal_and_flags_reach_port(self) -> None:
        await self.ctx.answer("好")
        self.assertEqual(len(self.port.calls), 1)
        self.assertIs(self.port.calls[0]["content"].kind, ContentKind.TEXT)
        self.assertIsNone(self.port.calls[0]["reply_ref"])
        self.assertFalse(self.port.calls[0]["mention"])

    async def test_mention_fragment_delegates(self) -> None:
        self.assertEqual(self.ctx.mention_fragment(), "@张三")
        self.assertEqual(
            [p.user for p in self.port.mentions], [self.ctx.event.principal.user]
        )


if __name__ == "__main__":
    unittest.main()
