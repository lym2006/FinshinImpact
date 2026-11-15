"""路由清单经分发链路走通

- 归一中间件把上下文注进处理函数，回执按清单顺序命中
- 频道与群里的越权命令按可见性静音
"""

import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from adapter_presence import adapter_present  # noqa: E402
from aiogram import Dispatcher  # noqa: E402
from aiogram.types import Chat, Message, Update, User  # noqa: E402

from bundled._shared.filters import CommandMatch  # noqa: E402
from bundled._shared.messages import BotMessage  # noqa: E402
from bundled.help import _commands  # noqa: E402
from finshin_sdk import HandlerContext  # noqa: E402
from finshin_sdk.domain import ContentKind, MessageRoute  # noqa: E402
from finshin_sdk.dto import MsgReferenceDTO, OutboundPayloadDTO  # noqa: E402

_GROUP = Chat(id=-100123, type="supergroup", title="测试群")
_PRIVATE = Chat(id=456, type="private")
_CHANNEL = Chat(id=-100999, type="channel", title="测试频道")
_USER = User(id=456, is_bot=False, first_name="三")
_BOT = User(id=777, is_bot=True, first_name="机器人", username="MyBot")

# 参与判定的菜单项，与实例启用集解耦
_MENU = {
    "help": "帮助",
    "history": "显示历史记录",
    "demo": "演示命令",
}


class _FakeBot:
    """只回答自身身份的假 bot

    - 路由与过滤器只取 id 与 me()
    """

    id = 777

    async def me(self) -> User:
        return _BOT


class _RecordingInteraction:
    """记录外发内容的假交互端口

    - 只实现 send_message 与 mention_fragment
    """

    def __init__(self) -> None:
        self.sent: list[str] = []
        self.payloads: list[OutboundPayloadDTO] = []
        self.replies: list[MsgReferenceDTO | None] = []

    async def send_message(
        self,
        principal: Any,
        payload: OutboundPayloadDTO,
        *,
        mention: bool = False,
        reply_ref: MsgReferenceDTO | None = None,
    ) -> MsgReferenceDTO | None:
        self.sent.append(payload.text)
        self.payloads.append(payload)
        self.replies.append(reply_ref)
        return None

    def mention_fragment(self, principal: Any) -> str:
        return ""


def _message(chat: Chat = _GROUP, **fields: Any) -> Message:
    """构造一条消息"""
    return Message(
        message_id=fields.pop("id", 7),
        date=fields.pop("date", datetime(2026, 10, 16, 12, 0)),
        chat=chat,
        from_user=fields.pop("from_user", _USER),
        content_type=fields.pop("content_type", "text"),
        **fields,
    )


_ADAPTER_LOADED = adapter_present()


@unittest.skipUnless(_ADAPTER_LOADED, "适配层未装载，集成链路用例跳过")
class TestCtxReachesHandlers(unittest.IsolatedAsyncioTestCase):
    """归一上下文经完整分发链路注入

    - 装配的是本体的帮助插件与适配层那两件
    """

    def setUp(self) -> None:
        from finshin_adapter_tg._normalize import NormalizeMiddleware
        from finshin_adapter_tg._router_bridge import build_router

        # 帮助图桩件要落在真实文件上，取体积那句读的就是它
        image = Path(tempfile.mkdtemp()) / "help.png"
        image.write_bytes(b"fake-png-bytes")
        for name, value in (
            ("help_list", _MENU),
            ("generate_image", lambda: image),
            ("resolve_single_help", lambda head: f"单命令:{head}"),
            ("resolve_usage_hint", lambda head: f"用法:{head}"),
        ):
            patcher = patch.object(_commands, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.interaction = _RecordingInteraction()
        self.ran: list[str] = []
        self.dispatcher = Dispatcher()
        self.dispatcher.update.outer_middleware(
            NormalizeMiddleware(self.interaction, bot=_FakeBot())  # type: ignore[arg-type]
        )

        # 帮助插件按清单编译成引擎对象，与另一只业务路由同台
        self.dispatcher.include_router(build_router(_commands.ROUTES))

        async def run_history(raw: Message, *, ctx: HandlerContext) -> None:
            self.ran.append("history")

        other = (MessageRoute(CommandMatch("history"), run_history),)
        self.dispatcher.include_router(build_router(other))

    async def _answer(self, text: str, chat: Chat = _PRIVATE) -> list[str]:
        """跑一条消息并回传外发文本

        - 每次先清空，多条用例互不攒账
        """
        self.interaction.sent.clear()
        self.interaction.payloads.clear()
        self.interaction.replies.clear()
        update = Update(update_id=1, message=_message(chat=chat, text=text))
        await self.dispatcher.feed_update(_FakeBot(), update)  # type: ignore[arg-type]
        return self.interaction.sent

    async def test_unknown_command_replies(self) -> None:
        self.assertEqual(await self._answer("/nope"), [BotMessage.CMD_NOT_FOUND])

    async def test_format_error_replies(self) -> None:
        self.assertEqual(await self._answer("/ nope"), [BotMessage.CMD_FORMAT_ERROR])

    async def test_other_bot_command_replies_format_error(self) -> None:
        self.assertEqual(
            await self._answer("/nope@otherbot"), [BotMessage.CMD_FORMAT_ERROR]
        )

    async def test_stray_flag_replies_usage(self) -> None:
        self.assertEqual(await self._answer("/help -x"), ["用法:help"])

    async def test_unknown_name_quiet_outside_private(self) -> None:
        for text in ("/nope", "/ nope", "/nope@otherbot"):
            for chat in (_GROUP, _CHANNEL):
                with self.subTest(text=text, scope=chat.type):
                    self.assertEqual(await self._answer(text, chat=chat), [])

    async def test_group_stray_replies_quoting_sender(self) -> None:
        cases = (
            ("/history 20", "用法:history"),
            ("/history -v", "用法:history"),
            ("/help -x", "用法:help"),
        )
        for text, expected in cases:
            with self.subTest(text=text):
                self.assertEqual(await self._answer(text, chat=_GROUP), [expected])
                self.assertEqual(self.ran, [])
                self.assertIsNotNone(self.interaction.replies[0])

    async def test_channel_stray_stays_quiet(self) -> None:
        for text in ("/history 20", "/history -v"):
            with self.subTest(text=text):
                self.assertEqual(await self._answer(text, chat=_CHANNEL), [])
                self.assertEqual(self.ran, [])

    async def test_private_stray_never_reaches_command(self) -> None:
        self.assertEqual(await self._answer("/history 20"), ["用法:history"])
        self.assertEqual(self.interaction.replies, [None])
        self.assertEqual(self.ran, [])

    async def test_bare_command_reaches_command(self) -> None:
        self.assertEqual(await self._answer("/history", chat=_GROUP), [])
        self.assertEqual(self.ran, ["history"])

    async def test_help_flag_takes_single_help(self) -> None:
        """带 -h 让给单命令帮助，命令侧拿不到"""
        self.assertEqual(await self._answer("/history -h"), ["单命令:history"])
        self.assertEqual(self.ran, [])

    async def test_menu_command_sends_photo(self) -> None:
        """裸 /help 出帮助图"""
        await self._answer("/help")
        payload = self.interaction.payloads[-1]
        self.assertEqual(payload.kind, ContentKind.PHOTO)
        self.assertTrue(str(payload.local_path).endswith("help.png"))

    async def test_plain_text_silent(self) -> None:
        self.assertEqual(await self._answer("随便聊聊"), [])


if __name__ == "__main__":
    unittest.main()
