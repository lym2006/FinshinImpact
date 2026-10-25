# devtools/tests/test_normalize.py
"""事件归一样例测试

- 覆盖作用域、内容种类、命令解析、点名与引用归属、中间件放行
"""

import sys
import unittest
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from aiogram.types import (  # noqa: E402
    Animation,
    Chat,
    Dice,
    Document,
    LivePhoto,
    Message,
    MessageEntity,
    PhotoSize,
    Update,
    User,
)

from adapters.telegram import _normalize as normalize_mod  # noqa: E402
from adapters.telegram._normalize import (  # noqa: E402
    BotIdentity,
    NormalizeMiddleware,
    normalize_update,
)
from core.domain import ChatScope, ContentKind  # noqa: E402

_GROUP = Chat(id=-100123, type="supergroup", title="测试群")
_PRIVATE = Chat(id=456, type="private")
_USER = User(id=456, is_bot=False, first_name="三", last_name="张")
_BOT = User(id=777, is_bot=True, first_name="机器人", username="MyBot")
_IDENTITY = BotIdentity(user_id="777", username="MyBot")
_NO_IDENTITY = BotIdentity()


class _FakeBot:
    """只回答自身身份的假 bot

    - 归一化中间件只取 me()
    """

    async def me(self) -> User:
        return _BOT


def _update(chat: Chat = _GROUP, **fields: Any) -> Update:
    """构造仅含一条消息的更新"""
    message = Message(
        message_id=fields.pop("message_id", 7),
        date=fields.pop("date", datetime(2026, 10, 16, 12, 0)),
        chat=chat,
        from_user=fields.pop("from_user", _USER),
        **fields,
    )
    return Update(update_id=1, message=message)


def _event(update: Update, identity: BotIdentity = _NO_IDENTITY) -> Any:
    """归一并断言非空"""
    event = normalize_update(update, identity=identity)
    assert event is not None
    return event


class TestScopeAndContent(unittest.TestCase):
    """作用域与内容归一"""

    def test_private_text(self) -> None:
        event = _event(_update(chat=_PRIVATE, text="你好"))
        self.assertEqual(event.scope, ChatScope.PRIVATE)
        self.assertEqual(event.content.text, "你好")
        self.assertEqual(event.content.media, ())
        self.assertEqual(event.principal.container, "u456")
        self.assertEqual(event.principal.key, "tg.u456.456")
        self.assertEqual(event.ref.key, "tg.u456.7")

    def test_group_container_and_name(self) -> None:
        event = _event(_update(text="在吗"))
        self.assertEqual(event.scope, ChatScope.GROUP)
        self.assertEqual(event.principal.container, "g100123")
        self.assertEqual(event.container_name, "测试群")
        self.assertEqual(event.display_name, "三 张")

    def test_photo_takes_caption(self) -> None:
        photo = PhotoSize(file_id="p", file_unique_id="u", width=90, height=90)
        big = PhotoSize(file_id="p", file_unique_id="u", width=800, height=600)
        event = _event(_update(photo=[photo, big], caption="附言"))
        self.assertEqual(event.content.text, "附言")
        self.assertEqual([m.kind for m in event.content.media], [ContentKind.PHOTO])

    def test_service_message_still_yields_event(self) -> None:
        event = _event(_update(new_chat_title="改名了"))
        self.assertEqual(event.content.text, "")
        self.assertEqual([m.kind for m in event.content.media], ["unknown"])

    def test_animation_wins_over_document(self) -> None:
        animation = Animation(
            file_id="a", file_unique_id="au", width=1, height=1, duration=1
        )
        document = Document(file_id="d", file_unique_id="du")
        event = _event(_update(animation=animation, document=document))
        self.assertEqual([m.kind for m in event.content.media], [ContentKind.ANIMATION])

    def test_live_photo_is_unknown(self) -> None:
        live = LivePhoto(
            file_id="l", file_unique_id="lu", width=1, height=1, duration=2
        )
        event = _event(_update(live_photo=live, caption="live"))
        self.assertEqual([m.kind for m in event.content.media], [ContentKind.UNKNOWN])
        self.assertEqual(event.content.text, "live")

    def test_dice_is_unknown_media(self) -> None:
        event = _event(_update(dice=Dice(value=3, emoji="🎲")))
        self.assertEqual([m.kind for m in event.content.media], [ContentKind.UNKNOWN])

    def test_non_message_update_returns_none(self) -> None:
        self.assertIsNone(normalize_update(Update(update_id=1)))


class TestCommandParsing(unittest.TestCase):
    """命令解析"""

    def test_plain_command(self) -> None:
        event = _event(_update(text="/history"))
        self.assertTrue(event.command.matched)
        self.assertEqual(
            (event.command.head, event.command.flags, event.command.args),
            ("history", (), ()),
        )

    def test_flag_and_args_split(self) -> None:
        event = _event(_update(text="/history -h 20"))
        self.assertTrue(event.command.matched)
        self.assertEqual(
            (event.command.head, event.command.flags, event.command.args),
            ("history", ("-h",), ("20",)),
        )

    def test_mention_is_format_error(self) -> None:
        for text in ("/history@mybot -h", "/history@Fool"):
            with self.subTest(text=text):
                event = _event(_update(text=text))
                self.assertFalse(event.command.matched)
                self.assertTrue(event.command.format_error)

    def test_stray_flag_shape_is_format_error(self) -> None:
        for text in ("/history -", "/history --x", "/history -9x"):
            with self.subTest(text=text):
                event = _event(_update(text=text))
                self.assertFalse(event.command.matched)
                self.assertTrue(event.command.format_error)

    def test_unknown_flag_keeps_shape(self) -> None:
        event = _event(_update(text="/history -x"))
        self.assertTrue(event.command.matched)
        self.assertEqual(event.command.flags, ("-x",))

    def test_space_not_stripped(self) -> None:
        event = _event(_update(text="/hist ory -h"))
        self.assertTrue(event.command.matched)
        self.assertEqual(
            (event.command.head, event.command.flags, event.command.args),
            ("hist", ("-h",), ("ory",)),
        )

    def test_gap_after_prefix_is_format_error(self) -> None:
        for text in ("/ history", "/", "/@mybot", "/-x"):
            with self.subTest(text=text):
                event = _event(_update(text=text))
                self.assertFalse(event.command.matched)
                self.assertTrue(event.command.format_error)

    def test_case_preserved(self) -> None:
        event = _event(_update(text="/HISTORY"))
        self.assertEqual(event.command.head, "HISTORY")

    def test_plain_text_is_not_command(self) -> None:
        event = _event(_update(text="你好 /history"))
        self.assertFalse(event.command.matched)
        self.assertFalse(event.command.format_error)


class TestMentionAndReply(unittest.TestCase):
    """点名与引用归属"""

    def _mention_event(self, text: str, length: int, offset: int = 0) -> Any:
        """按 mention 实体归一并回传事件"""
        entity = MessageEntity(type="mention", offset=offset, length=length)
        return _event(_update(text=text, entities=[entity]), _IDENTITY)

    def test_mention_hits_bot(self) -> None:
        self.assertTrue(self._mention_event("@MyBot 在吗", 6).is_mention_bot)

    def test_mention_uses_utf16_offset(self) -> None:
        self.assertTrue(
            self._mention_event("🎉🎉 @MyBot 在吗", 6, offset=5).is_mention_bot
        )

    def test_mention_other_bot_ignored(self) -> None:
        self.assertFalse(self._mention_event("@Other 在吗", 6).is_mention_bot)

    def test_text_mention_hits_bot_id(self) -> None:
        entity = MessageEntity(type="text_mention", offset=0, length=2, user=_BOT)
        event = _event(_update(text="点了你", entities=[entity]), _IDENTITY)
        self.assertTrue(event.is_mention_bot)

    def test_identity_unknown_marks_nothing(self) -> None:
        event = _event(_update(text="@MyBot 在吗"))
        self.assertFalse(event.is_mention_bot)

    def test_reply_to_bot_marked(self) -> None:
        quoted = Message(
            message_id=3,
            date=datetime(2026, 10, 16, 11, 0),
            chat=_GROUP,
            from_user=_BOT,
            text="我答过的话",
        )
        event = _event(_update(text="接着说", reply_to_message=quoted), _IDENTITY)
        self.assertTrue(event.reply_to_bot)
        self.assertEqual(event.reply_text, "我答过的话")

    def test_reply_from_user_not_marked(self) -> None:
        quoted = Message(
            message_id=3,
            date=datetime(2026, 10, 16, 11, 0),
            chat=_GROUP,
            from_user=_USER,
            text="他人发言",
        )
        event = _event(_update(text="追问", reply_to_message=quoted), _IDENTITY)
        self.assertFalse(event.reply_to_bot)


class TestReply(unittest.TestCase):
    """引用取数"""

    def test_reply_ref_and_text(self) -> None:
        quoted = Message(
            message_id=3,
            date=datetime(2026, 10, 16, 11, 0),
            chat=_GROUP,
            from_user=_USER,
            text="被引用的提问",
        )
        event = _event(_update(text="接着说", reply_to_message=quoted))
        assert event.reply_ref is not None
        self.assertEqual(event.reply_ref.message_id, "3")
        self.assertEqual(event.reply_text, "被引用的提问")

    def test_reply_caption_used(self) -> None:
        photo = PhotoSize(file_id="p", file_unique_id="u", width=1, height=1)
        quoted = Message(
            message_id=4,
            date=datetime(2026, 10, 16, 11, 0),
            chat=_GROUP,
            from_user=_USER,
            photo=[photo],
            caption="图说",
        )
        event = _event(_update(text="?", reply_to_message=quoted))
        self.assertEqual(event.reply_text, "图说")

    def test_without_reply(self) -> None:
        event = _event(_update(text="你好"))
        self.assertIsNone(event.reply_ref)
        self.assertEqual(event.reply_text, "")


class TestAnonymousSender(unittest.TestCase):
    """匿名与频道代发"""

    def test_sender_chat_used(self) -> None:
        sender = Chat(id=-100999, type="channel", title="频道名")
        event = _event(_update(from_user=None, sender_chat=sender, text="广播"))
        self.assertEqual(event.display_name, "频道名")
        self.assertEqual(event.principal.user, "unknown")
        self.assertEqual(event.principal.container, "g100123")

    def test_no_sender_at_all(self) -> None:
        event = _event(_update(from_user=None, text="系统"))
        self.assertEqual(event.display_name, "")


class TestNormalizeMiddleware(unittest.IsolatedAsyncioTestCase):
    """归一化中间件"""

    async def _run(self, event: Update) -> Any:
        """走一遍中间件并回传下游收到的 data"""
        seen: dict[str, Any] = {}

        async def _next(evt: Any, data: dict[str, Any]) -> str:
            seen.update(data)
            return "passed"

        middleware = NormalizeMiddleware(None, bot=_FakeBot())  # type: ignore[arg-type]
        result = await middleware(_next, event, {})
        self.assertEqual(result, "passed")
        return seen

    async def test_injects_ctx_only(self) -> None:
        seen = await self._run(_update(chat=_PRIVATE, text="你好"))
        self.assertEqual(set(seen), {"ctx"})
        self.assertEqual(seen["ctx"].event.content.text, "你好")

    async def test_ctx_carries_bot_identity(self) -> None:
        entity = MessageEntity(type="mention", offset=0, length=6)
        seen = await self._run(_update(text="@MyBot 在吗", entities=[entity]))
        self.assertTrue(seen["ctx"].event.is_mention_bot)

    async def test_non_message_update_not_injected(self) -> None:
        seen = await self._run(Update(update_id=1))
        self.assertEqual(seen, {})

    async def test_normalize_error_still_passes_through(self) -> None:
        with patch.object(
            normalize_mod, "normalize_update", side_effect=RuntimeError("boom")
        ):
            seen = await self._run(_update(text="你好"))
        self.assertEqual(seen, {})


if __name__ == "__main__":
    unittest.main()
