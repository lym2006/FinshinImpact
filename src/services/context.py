# src/services/context.py
"""处理上下文

- 组装事件与交互端口供 handler 消费
"""

from dataclasses import dataclass

from core.contracts import InteractionPort
from core.domain import ContentKind
from core.dto import InboundEventDTO, MsgReferenceDTO, OutboundPayloadDTO


@dataclass(frozen=True, slots=True)
class HandlerContext:
    """处理上下文

    - handler 经此取入站事件与外发端口
    """

    event: InboundEventDTO
    interaction: InteractionPort

    async def reply(self, content: str | OutboundPayloadDTO) -> MsgReferenceDTO | None:
        """回复当前事件"""
        return await self.interaction.send_message(
            self.event.principal,
            _to_payload(content),
            reply_ref=self.event.ref,
        )

    async def answer(
        self, content: str | OutboundPayloadDTO, *, mention: bool = False
    ) -> MsgReferenceDTO | None:
        """发到当前会话，不引用原消息

        - mention 为真时正文前拼上发起人，用于群里点名回执
        """
        return await self.interaction.send_message(
            self.event.principal, _to_payload(content), mention=mention
        )

    def mention_fragment(self) -> str:
        """取当前主体的提及片段"""
        return self.interaction.mention_fragment(self.event.principal)


def _to_payload(content: str | OutboundPayloadDTO) -> OutboundPayloadDTO:
    """文字归一为外发负载"""
    if isinstance(content, OutboundPayloadDTO):
        return content
    return OutboundPayloadDTO(kind=ContentKind.TEXT, text=content)
