# devtools/tests/test_interaction.py
"""Telegram 交互端口样例测试

- 覆盖容器段反推、分段阈值、发送分派、错误翻译与存在性探测
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from aiogram.exceptions import TelegramAPIError  # noqa: E402
from aiogram.methods import SendMessage  # noqa: E402

from adapters.telegram._interaction import (  # noqa: E402
    TelegramInteractionPort,
    _chat_id_of,
    _split_chunks,
)
from core.domain import ContentKind, Platform  # noqa: E402
from core.domain.ids import ContainerKey, MessageId, UserId  # noqa: E402
from core.dto import (  # noqa: E402
    MsgReferenceDTO,
    OutboundPayloadDTO,
    PrincipalDTO,
)
from exceptions import MessageVanishedError  # noqa: E402

_SEGMENT = 4000


def _principal(container: str = "u456", user: str = "456") -> PrincipalDTO:
    return PrincipalDTO(
        platform=Platform.TELEGRAM,
        container=ContainerKey(container),
        user=UserId(user),
    )


def _ref(container: str = "u456", message_id: str = "7") -> MsgReferenceDTO:
    return MsgReferenceDTO(
        platform=Platform.TELEGRAM,
        container=ContainerKey(container),
        message_id=MessageId(message_id),
    )


def _api_error(message: str) -> TelegramAPIError:
    return TelegramAPIError(method=SendMessage(chat_id=1, text="x"), message=message)


class _FakeSent:
    def __init__(self, message_id: int) -> None:
        self.message_id = message_id


class _FakeBot:
    def __init__(
        self, error: Exception | None = None, only: set[str] | None = None
    ) -> None:
        self.error = error
        self.only = only
        self.calls: list[tuple[str, dict]] = []

    def _record(self, name: str, **kwargs: object) -> _FakeSent:
        self.calls.append((name, kwargs))
        if self.error is not None and (self.only is None or name in self.only):
            raise self.error
        return _FakeSent(999)

    async def send_message(self, **kwargs: object) -> _FakeSent:
        return self._record("send_message", **kwargs)

    async def send_photo(self, **kwargs: object) -> _FakeSent:
        return self._record("send_photo", **kwargs)

    async def send_video(self, **kwargs: object) -> _FakeSent:
        return self._record("send_video", **kwargs)

    async def send_animation(self, **kwargs: object) -> _FakeSent:
        return self._record("send_animation", **kwargs)

    async def send_voice(self, **kwargs: object) -> _FakeSent:
        return self._record("send_voice", **kwargs)

    async def send_document(self, **kwargs: object) -> _FakeSent:
        return self._record("send_document", **kwargs)

    async def edit_message_text(self, **kwargs: object) -> _FakeSent:
        return self._record("edit_message_text", **kwargs)


class TestContainerReverse(unittest.TestCase):
    """容器段反推"""

    def test_group_takes_negative(self) -> None:
        self.assertEqual(_chat_id_of(ContainerKey("g100123")), -100123)

    def test_private_takes_user_id(self) -> None:
        self.assertEqual(_chat_id_of(ContainerKey("u456")), 456)

    def test_empty_container_rejected(self) -> None:
        with self.assertRaises(ValueError):
            _chat_id_of(ContainerKey(""))


class TestChunking(unittest.TestCase):
    """分段切片"""

    def test_boundaries(self) -> None:
        cases = {
            _SEGMENT: 1,
            _SEGMENT + 1: 2,
            _SEGMENT * 2: 2,
            _SEGMENT * 5: 5,
            _SEGMENT * 6: 6,
        }
        for length, expected in cases.items():
            with self.subTest(length=length):
                chunks = _split_chunks("x" * length)
                self.assertEqual(len(chunks), expected)
                self.assertEqual("".join(chunks), "x" * length)


class TestSendDispatch(unittest.IsolatedAsyncioTestCase):
    """发送分派"""

    async def asyncSetUp(self) -> None:
        self.bot = _FakeBot()
        self.port = TelegramInteractionPort(self.bot)  # type: ignore[arg-type]

    async def test_text_single_call(self) -> None:
        ref = await self.port.send_message(
            _principal(), OutboundPayloadDTO(kind=ContentKind.TEXT, text="你好")
        )
        name, kwargs = self.bot.calls[0]
        self.assertEqual(name, "send_message")
        self.assertEqual(kwargs["chat_id"], 456)
        self.assertEqual(kwargs["text"], "你好")
        self.assertIsNone(kwargs["reply_to_message_id"])
        assert ref is not None
        self.assertEqual(ref.message_id, "999")

    async def test_long_text_split_with_sleep(self) -> None:
        with patch("adapters.telegram._interaction.asyncio.sleep", new=AsyncMock()):
            await self.port.send_message(
                _principal(),
                OutboundPayloadDTO(kind=ContentKind.TEXT, text="x" * (_SEGMENT * 6)),
            )
        self.assertEqual(len(self.bot.calls), 6)

    async def test_threshold_chunks_do_not_sleep(self) -> None:
        with patch(
            "adapters.telegram._interaction.asyncio.sleep", new_callable=AsyncMock
        ) as sleep:
            await self.port.send_message(
                _principal(),
                OutboundPayloadDTO(kind=ContentKind.TEXT, text="x" * (_SEGMENT * 5)),
            )
        sleep.assert_not_awaited()
        self.assertEqual(len(self.bot.calls), 5)

    async def test_mention_prepends_link(self) -> None:
        await self.port.send_message(
            _principal(),
            OutboundPayloadDTO(kind=ContentKind.TEXT, text="点名"),
            mention=True,
        )
        text = self.bot.calls[0][1]["text"]
        self.assertTrue(text.startswith("[456](tg://user?id=456) 点名"))

    async def test_reply_ref_passed(self) -> None:
        await self.port.send_message(
            _principal("g100123", "456"),
            OutboundPayloadDTO(kind=ContentKind.TEXT, text="群答"),
            reply_ref=_ref("g100123", "77"),
        )
        _, kwargs = self.bot.calls[0]
        self.assertEqual(kwargs["chat_id"], -100123)
        self.assertEqual(kwargs["reply_to_message_id"], 77)

    async def test_photo_uses_send_photo_and_caption(self) -> None:
        await self.port.send_message(
            _principal(),
            OutboundPayloadDTO(kind=ContentKind.PHOTO, local_path="a.png", text="图说"),
        )
        name, kwargs = self.bot.calls[0]
        self.assertEqual(name, "send_photo")
        self.assertEqual(kwargs["caption"], "图说")

    async def test_document_uses_send_document(self) -> None:
        await self.port.send_message(
            _principal(),
            OutboundPayloadDTO(
                kind=ContentKind.DOCUMENT,
                local_path="temp/u456.md",
                file_name="记录.md",
                text="附言",
            ),
        )
        name, kwargs = self.bot.calls[0]
        self.assertEqual(name, "send_document")
        self.assertEqual(kwargs["document"].filename, "记录.md")

    async def test_media_without_caption_passes_none(self) -> None:
        await self.port.send_message(
            _principal(), OutboundPayloadDTO(kind=ContentKind.PHOTO, local_path="a.png")
        )
        self.assertIsNone(self.bot.calls[0][1]["caption"])

    async def test_video_animation_audio_take_native_form(self) -> None:
        cases = (
            (ContentKind.VIDEO, "send_video", "video"),
            (ContentKind.ANIMATION, "send_animation", "animation"),
            (ContentKind.AUDIO, "send_voice", "voice"),
        )
        for kind, expected_name, arg in cases:
            with self.subTest(kind=kind):
                await self.port.send_message(
                    _principal(), OutboundPayloadDTO(kind=kind, local_path="a.bin")
                )
                name, kwargs = self.bot.calls[-1]
                self.assertEqual(name, expected_name)
                self.assertIn(arg, kwargs)

    async def test_audio_rejected_falls_back_to_document(self) -> None:
        bot = _FakeBot(
            _api_error("Bad Request: can't parse OGG entity"), only={"send_voice"}
        )
        port = TelegramInteractionPort(bot)  # type: ignore[arg-type]
        await port.send_message(
            _principal(), OutboundPayloadDTO(kind=ContentKind.AUDIO, local_path="a.mp3")
        )
        self.assertEqual(
            [name for name, _ in bot.calls], ["send_voice", "send_document"]
        )

    async def test_oversized_photo_falls_back_to_document(self) -> None:
        bot = _FakeBot(_api_error("Bad Request: file is too big"), only={"send_photo"})
        port = TelegramInteractionPort(bot)  # type: ignore[arg-type]
        await port.send_message(
            _principal(), OutboundPayloadDTO(kind=ContentKind.PHOTO, local_path="a.png")
        )
        self.assertEqual(
            [name for name, _ in bot.calls], ["send_photo", "send_document"]
        )

    async def test_document_failure_not_retried(self) -> None:
        bot = _FakeBot(_api_error("Bad Request: file is too big"))
        port = TelegramInteractionPort(bot)  # type: ignore[arg-type]
        with self.assertRaises(TelegramAPIError):
            await port.send_message(
                _principal(),
                OutboundPayloadDTO(kind=ContentKind.DOCUMENT, local_path="a.md"),
            )
        self.assertEqual(len(bot.calls), 1)

    async def test_vanished_reply_not_retried_as_document(self) -> None:
        bot = _FakeBot(
            _api_error("Bad Request: message to be replied not found"),
            only={"send_photo"},
        )
        port = TelegramInteractionPort(bot)  # type: ignore[arg-type]
        with self.assertRaises(MessageVanishedError):
            await port.send_message(
                _principal(),
                OutboundPayloadDTO(kind=ContentKind.PHOTO, local_path="a.png"),
                reply_ref=_ref(message_id="77"),
            )
        self.assertEqual(len(bot.calls), 1)

    async def test_unknown_kind_rejected(self) -> None:
        with self.assertRaises(ValueError):
            await self.port.send_message(
                _principal(), OutboundPayloadDTO(kind=ContentKind.UNKNOWN)
            )


class TestErrorTranslation(unittest.IsolatedAsyncioTestCase):
    """发送错误翻译"""

    async def test_vanished_reply_becomes_domain_error(self) -> None:
        bot = _FakeBot(_api_error("Bad Request: message to be replied not found"))
        port = TelegramInteractionPort(bot)  # type: ignore[arg-type]
        with self.assertRaises(MessageVanishedError):
            await port.send_message(
                _principal(),
                OutboundPayloadDTO(kind=ContentKind.TEXT, text="x"),
                reply_ref=_ref(message_id="77"),
            )

    async def test_other_error_rethrown_as_is(self) -> None:
        bot = _FakeBot(_api_error("Bad Request: chat not found"))
        port = TelegramInteractionPort(bot)  # type: ignore[arg-type]
        with self.assertRaises(TelegramAPIError):
            await port.send_message(
                _principal(), OutboundPayloadDTO(kind=ContentKind.TEXT, text="x")
            )


class TestProbeExistence(unittest.IsolatedAsyncioTestCase):
    """存在性探测"""

    async def test_vanished_mark_reports_false(self) -> None:
        bot = _FakeBot(_api_error("Bad Request: message to edit not found"))
        port = TelegramInteractionPort(bot)  # type: ignore[arg-type]
        self.assertFalse(await port.probe_existence(_ref()))

    async def test_other_error_reports_true(self) -> None:
        bot = _FakeBot(_api_error("Bad Request: message can't be edited"))
        port = TelegramInteractionPort(bot)  # type: ignore[arg-type]
        self.assertTrue(await port.probe_existence(_ref("g100123", "8")))

    async def test_edit_accepted_reports_true(self) -> None:
        bot = _FakeBot()
        port = TelegramInteractionPort(bot)  # type: ignore[arg-type]
        self.assertTrue(await port.probe_existence(_ref("g100123", "8")))
        _, kwargs = bot.calls[0]
        self.assertEqual(kwargs["chat_id"], -100123)
        self.assertEqual(kwargs["message_id"], 8)


if __name__ == "__main__":
    unittest.main()
