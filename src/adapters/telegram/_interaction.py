# src/adapters/telegram/_interaction.py
"""Telegram 交互端口

- 实现统一发送、存在性探测与提及片段
"""

import asyncio
from collections.abc import Awaitable
from typing import TYPE_CHECKING

from aiogram.exceptions import TelegramAPIError
from aiogram.types import FSInputFile, Message

from core.contracts import InteractionPort
from core.domain import ContentKind
from core.domain.ids import ContainerKey
from core.dto import MsgReferenceDTO, OutboundPayloadDTO, PrincipalDTO

from ._errors import is_vanished, translate
from ._normalize import build_ref

if TYPE_CHECKING:
    from aiogram import Bot

# 外发分段
_SEGMENT_SIZE = 4000  # 字符，平台上限 4096 留 96 给提及前缀与实体偏移
_FLOOD_THRESHOLD = 5  # 段，总段数超此值时段间休眠防频控
_SEGMENT_SLEEP_SECONDS = 1.0  # 秒

_GROUP_PREFIX = "g"
_PROBE_TEXT = "dummy"  # 探测占位文本，仅用于触发服务端错误串


def _chat_id_of(container: ContainerKey) -> int:
    """容器段反推会话 id

    - 容器段格式由 core.domain.make_container 定义
    - 群聊 g 前缀补负号，私聊 u 前缀即用户 id
    """
    if not container:
        raise ValueError("容器段为空，无法定位会话")
    if container.startswith(_GROUP_PREFIX):
        return -int(container[1:])
    return int(container[1:])


def _split_chunks(text: str) -> list[str]:
    """按分段阈值切片"""
    return [text[i : i + _SEGMENT_SIZE] for i in range(0, len(text), _SEGMENT_SIZE)]


def _reply_id(reply_ref: MsgReferenceDTO | None) -> int | None:
    """引用目标转消息 id"""
    return int(reply_ref.message_id) if reply_ref is not None else None


class TelegramInteractionPort(InteractionPort):
    """Telegram 交互端口"""

    def __init__(self, bot: "Bot") -> None:
        self._bot = bot

    async def send_message(
        self,
        principal: PrincipalDTO,
        content: OutboundPayloadDTO,
        *,
        mention: bool = False,
        reply_ref: MsgReferenceDTO | None = None,
    ) -> MsgReferenceDTO | None:
        """发送消息

        - 超长文字自动分段
        - 媒体附言走 caption
        """
        if content.kind == ContentKind.TEXT:
            return await self._send_text(
                principal, content.text, mention=mention, reply_ref=reply_ref
            )
        if content.kind == ContentKind.UNKNOWN:
            raise ValueError(f"不支持的外发内容种类: {content.kind}")
        return await self._send_media(principal, content, reply_ref=reply_ref)

    async def probe_existence(self, target: MsgReferenceDTO) -> bool:
        """探测消息是否仍存在

        - 靠 dummy edit 的错误串区分已删除与无权编辑
        - 目标是用户消息，bot 无权编辑他人消息，不会真改动内容
        - 禁止用于探测 bot 自己发的消息，文本会被真改成占位串
        """
        try:
            await self._bot.edit_message_text(
                chat_id=_chat_id_of(target.container),
                message_id=int(target.message_id),
                text=_PROBE_TEXT,
            )
        except TelegramAPIError as exc:
            return not is_vanished(exc)
        return True

    def mention_fragment(self, principal: PrincipalDTO) -> str:
        """生成提及文本片段

        - 名称取 user 段，深链只靠 id
        """
        return f"[{principal.user}](tg://user?id={principal.user})"

    async def _send_text(
        self,
        principal: PrincipalDTO,
        text: str,
        *,
        mention: bool,
        reply_ref: MsgReferenceDTO | None,
    ) -> MsgReferenceDTO | None:
        """发送文字，超长分段"""
        body = f"{self.mention_fragment(principal)} {text}" if mention else text
        chunks = _split_chunks(body)
        sent: Message | None = None
        for index, chunk in enumerate(chunks):
            sent = await self._invoke(
                self._bot.send_message(
                    chat_id=_chat_id_of(principal.container),
                    text=chunk,
                    reply_to_message_id=_reply_id(reply_ref),
                ),
                reply_ref,
            )
            if len(chunks) > _FLOOD_THRESHOLD and index < len(chunks) - 1:
                await asyncio.sleep(_SEGMENT_SLEEP_SECONDS)

        return build_ref(sent, principal.container) if sent is not None else None

    async def _send_media(
        self,
        principal: PrincipalDTO,
        content: OutboundPayloadDTO,
        *,
        reply_ref: MsgReferenceDTO | None,
    ) -> MsgReferenceDTO | None:
        """发送媒体，file_name 缺省取路径末段"""
        file = FSInputFile(content.local_path, filename=content.file_name or None)
        caption = content.text or None
        chat_id = _chat_id_of(principal.container)
        if content.kind == ContentKind.PHOTO:
            sent = await self._invoke(
                self._bot.send_photo(
                    chat_id=chat_id,
                    photo=file,
                    caption=caption,
                    reply_to_message_id=_reply_id(reply_ref),
                ),
                reply_ref,
            )
        else:
            sent = await self._invoke(
                self._bot.send_document(
                    chat_id=chat_id,
                    document=file,
                    caption=caption,
                    reply_to_message_id=_reply_id(reply_ref),
                ),
                reply_ref,
            )

        return build_ref(sent, principal.container)

    async def _invoke(
        self, awaitable: Awaitable[Message], reply_ref: MsgReferenceDTO | None
    ) -> Message:
        """执行发送并翻译已删除错误

        - 无引用目标时原样上抛，平台错误串与删除无关
        """
        try:
            return await awaitable
        except TelegramAPIError as exc:
            if reply_ref is not None:
                raise translate(exc, reply_ref) from None
            raise
