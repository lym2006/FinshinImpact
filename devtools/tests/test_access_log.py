# devtools/tests/test_access_log.py
"""访问日志样例测试

- 条目按归一事件拼，图片张数取媒体条目数
- 引用与逐张附文各列一段，缺身份时按占位兜底
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

from aiogram.types import Chat, Message, PhotoSize, Update, User  # noqa: E402

from adapters.telegram._event import normalize_album, normalize_update  # noqa: E402
from services.context import HandlerContext  # noqa: E402
from utils.middleware import LoggingMiddleware  # noqa: E402

_GROUP = Chat(id=-100123, type="supergroup", title="测试群")
_PRIVATE = Chat(id=456, type="private", first_name="小明")
_USER = User(id=456, is_bot=False, first_name="三", last_name="张")
_OTHER = User(id=123, is_bot=False, first_name="四")

_SIZES = [
    PhotoSize(file_id=f"s{i}", file_unique_id=f"u{i}", width=10 * i, height=10 * i)
    for i in (1, 2, 3)
]


def _message(chat: Chat = _GROUP, **fields: Any) -> Message:
    """构造一条消息"""
    return Message(
        message_id=fields.pop("message_id", 7),
        date=fields.pop("date", datetime(2026, 10, 16, 12, 0)),
        chat=chat,
        from_user=fields.pop("from_user", _USER),
        **fields,
    )


def _event_of(message: Message) -> Any:
    """归一并断言非空"""
    event = normalize_update(Update(update_id=1, message=message))
    assert event is not None
    return event


def _album_event(*items: Message) -> Any:
    """并组并断言非空"""
    event = normalize_album(items)
    assert event is not None
    return event


def _album_message(message_id: int, caption: str | None = None) -> Message:
    """构造一条相册内消息"""
    return _message(
        message_id=message_id, photo=[_SIZES[0]], caption=caption, media_group_id="g1"
    )


def _entry(event: Any) -> str:
    """走日志拼装"""
    return LoggingMiddleware()._build_log_entry(event)


class TestEntry(unittest.TestCase):
    """条目正文段"""

    def test_private_text(self) -> None:
        """私聊文本报长度与正文"""
        entry = _entry(_event_of(_message(chat=_PRIVATE, text="你好")))
        self.assertEqual(
            entry,
            "[tg] 私聊[u456]<小明> | 用户456<三 张> 发送 [长度：2] 文本：你好",
        )

    def test_photo_sizes_count_once(self) -> None:
        """同图三档分辨率只算一张"""
        entry = _entry(_event_of(_message(photo=_SIZES)))
        self.assertIn("图片消息：1张", entry)

    def test_album_counts_items(self) -> None:
        """整组按条目计张数"""
        messages = [
            _album_message(10, "图集"),
            _album_message(11, "次张"),
            _album_message(12),
        ]
        entry = _entry(_album_event(*messages))
        self.assertIn("图片消息：3张", entry)

    def test_caption_listed_per_item(self) -> None:
        """附文逐张单列并带该张消息 id"""
        messages = [_album_message(10, "图集"), _album_message(11, "次张")]
        entry = _entry(_album_event(*messages))
        self.assertIn("附文[10]图集", entry)
        self.assertIn("附文[11]次张", entry)

    def test_reply_shows_sender_and_text(self) -> None:
        """引用段给出被引发言人与原文"""
        reply = _message(message_id=3, from_user=_OTHER, text="在吗")
        entry = _entry(_event_of(_message(text="在的", reply_to_message=reply)))
        self.assertIn("引用 用户123<四>「在吗」", entry)

    def test_long_text_truncated(self) -> None:
        """正文超上限截断并加省略号"""
        entry = _entry(_event_of(_message(text="字" * 61)))
        self.assertIn("[长度：61] 文本：" + "字" * 60 + "...", entry)

    def test_anonymous_sender_falls_back(self) -> None:
        """无发言人无群名按占位兜底"""
        chat = Chat(id=-100999, type="channel")
        entry = _entry(_event_of(_message(chat=chat, from_user=None, text="公告")))
        self.assertIn("[tg] 未知[]<未知聊天>", entry)
        self.assertIn("用户unknown<无名氏>", entry)


async def _noop_handler(event: Any, data: dict[str, Any]) -> str:
    return "passed"


class TestMiddleware(unittest.IsolatedAsyncioTestCase):
    """上下文取用与放行"""

    async def test_logged_when_ctx_present(self) -> None:
        middleware = LoggingMiddleware()
        event = _event_of(_message(chat=_PRIVATE, text="你好"))
        ctx = HandlerContext(event=event, interaction=None)  # type: ignore[arg-type]
        data = {"ctx": ctx}

        with patch.object(middleware._logger, "info") as info:
            result = await middleware(_noop_handler, Update(update_id=1), data)

        self.assertEqual(result, "passed")
        self.assertEqual(info.call_args_list[0].args[0], _entry(event))

    async def test_silent_without_ctx(self) -> None:
        middleware = LoggingMiddleware()
        update = Update(update_id=1)

        with patch.object(middleware._logger, "info") as info:
            result = await middleware(_noop_handler, update, {})

        self.assertEqual(result, "passed")
        info.assert_not_called()


if __name__ == "__main__":
    unittest.main()
