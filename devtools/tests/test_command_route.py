# devtools/tests/test_command_route.py
"""命令路由样例测试

- 覆盖帮助插件的形态回执、AI 触发优先级与中间件 ctx 注入
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

from utils import config_manager  # noqa: E402

_AI_SEED = {
    "chore.owner": "456",
    "chore.triggers": ["触发词"],
}

with patch.object(config_manager, "get", lambda path, _type: _AI_SEED[path]):
    from plugins.AI.handlers import _ai_chat  # noqa: E402

from aiogram import Dispatcher  # noqa: E402
from aiogram.types import (  # noqa: E402
    Chat,
    Message,
    MessageEntity,
    Update,
    User,
)

from adapters.telegram._event import BotIdentity, normalize_update  # noqa: E402
from adapters.telegram._normalize import NormalizeMiddleware  # noqa: E402
from adapters.telegram.router_bridge import build_router  # noqa: E402
from plugins._shared.filters import CommandMatch  # noqa: E402
from plugins._shared.messages import BotMessage  # noqa: E402
from plugins.help import _commands  # noqa: E402
from core.domain import ContentKind, PluginRoute, PluginSpec  # noqa: E402
from core.dto import (  # noqa: E402
    HelpCommandDTO,
    HelpFlagDTO,
    MsgReferenceDTO,
    OutboundPayloadDTO,
)
from services.context import HandlerContext  # noqa: E402

_GROUP = Chat(id=-100123, type="supergroup", title="测试群")
_PRIVATE = Chat(id=456, type="private")
_CHANNEL = Chat(id=-100999, type="channel", title="测试频道")
_USER = User(id=456, is_bot=False, first_name="三")
_BOT = User(id=777, is_bot=True, first_name="机器人", username="MyBot")
_IDENTITY = BotIdentity(user_id="777", username="MyBot")

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


class _StubAIConfig:
    """只提供触发词表的假 AI 配置"""

    group_triggers = ("触发词",)


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


def _ctx(message: Message) -> HandlerContext:
    """按假 bot 身份归一并组上下文"""
    event = normalize_update(Update(update_id=1, message=message), identity=_IDENTITY)
    assert event is not None
    return HandlerContext(event=event, interaction=_RecordingInteraction())


class _VerdictMixin:
    """回执与单命令帮助的双标记判定"""

    reject: Any
    keyword: Any

    async def _verdict(self, text: str, chat: Chat = _PRIVATE) -> tuple[bool, bool]:
        """回传（接管回执, 命中单命令帮助）"""
        message = _message(chat=chat, text=text)
        ctx = _ctx(message)
        return (await self.reject(ctx), await self.keyword(ctx))


class TestHelpCommandReject(_VerdictMixin, unittest.IsolatedAsyncioTestCase):
    """帮助插件的形态回执判定"""

    def setUp(self) -> None:
        patcher = patch.object(_commands, "help_list", _MENU)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.reject = _commands._is_illegal_command
        self.keyword = _commands._is_single_help

    async def test_unknown_name_taken(self) -> None:
        rejected, _ = await self._verdict("/nope")
        self.assertTrue(rejected)

    async def test_space_split_is_unknown_name(self) -> None:
        rejected, _ = await self._verdict("/hel p")
        self.assertTrue(rejected)

    async def test_gap_after_prefix_is_taken(self) -> None:
        rejected, _ = await self._verdict("/ help")
        self.assertTrue(rejected)

    async def test_menu_command_not_taken(self) -> None:
        rejected, _ = await self._verdict("/help")
        self.assertFalse(rejected)

    async def test_command_for_other_bot_is_taken(self) -> None:
        rejected, _ = await self._verdict("/nope@otherbot")
        self.assertTrue(rejected)

    async def test_group_chat_leaves_unknown_quiet(self) -> None:
        for text in ("/nope", "/ help", "/nope@otherbot"):
            with self.subTest(text=text):
                rejected, listed = await self._verdict(text, chat=_GROUP)
                self.assertFalse(rejected)
                self.assertFalse(listed)

    async def test_group_chat_takes_stray_quietly(self) -> None:
        rejected, listed = await self._verdict("/help -x", chat=_GROUP)
        self.assertTrue(rejected)
        self.assertFalse(listed)

    async def test_group_keyword_still_helps(self) -> None:
        rejected, listed = await self._verdict("/help -h", chat=_GROUP)
        self.assertFalse(rejected)
        self.assertTrue(listed)

    async def test_mention_is_format_error(self) -> None:
        rejected, listed = await self._verdict("/history@MYBOT -h")
        self.assertTrue(rejected)
        self.assertFalse(listed)

    async def test_keyword_hit_with_own_flag(self) -> None:
        rejected, listed = await self._verdict("/history -h")
        self.assertFalse(rejected)
        self.assertTrue(listed)

    async def test_keyword_miss_without_flag(self) -> None:
        _, listed = await self._verdict("/history")
        self.assertFalse(listed)

    async def test_unknown_flag_taken_as_stray(self) -> None:
        rejected, listed = await self._verdict("/history -x")
        self.assertTrue(rejected)
        self.assertFalse(listed)

    async def test_positional_arg_taken_as_stray(self) -> None:
        rejected, listed = await self._verdict("/history 20")
        self.assertTrue(rejected)
        self.assertFalse(listed)

    async def test_repeated_flag_taken_as_stray(self) -> None:
        rejected, listed = await self._verdict("/help -h -h")
        self.assertTrue(rejected)
        self.assertFalse(listed)

    async def test_multiple_flags_taken_as_stray(self) -> None:
        rejected, listed = await self._verdict("/history -a -b")
        self.assertTrue(rejected)
        self.assertFalse(listed)


class TestArgsAllowedCommand(_VerdictMixin, unittest.IsolatedAsyncioTestCase):
    """认位置参数的命令放行给业务侧"""

    def setUp(self) -> None:
        menu = {**_MENU, "grant": "主人授权", "clear": "清记忆"}
        patcher = patch.object(_commands, "help_list", menu)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.reject = _commands._is_illegal_command
        self.keyword = _commands._is_single_help

    async def test_grant_with_id_yields_in_both_scopes(self) -> None:
        """私聊与群聊都放行给授权命令"""
        for chat in (_PRIVATE, _GROUP):
            with self.subTest(scope=chat.type):
                rejected, listed = await self._verdict("/grant 12345", chat=chat)
                self.assertFalse(rejected)
                self.assertFalse(listed)

    async def test_grant_with_help_flag_lists(self) -> None:
        """带 -h 仍出单命令帮助"""
        rejected, listed = await self._verdict("/grant -h")
        self.assertFalse(rejected)
        self.assertTrue(listed)

    async def test_other_command_with_text_still_taken(self) -> None:
        """没进名单的命令带字照旧拦"""
        rejected, _ = await self._verdict("/clear 快点")
        self.assertTrue(rejected)


class TestCommandFlagSpec(_VerdictMixin, unittest.IsolatedAsyncioTestCase):
    """插件清单登记的 flag 口径"""

    def setUp(self) -> None:
        specs = {
            "demo": HelpCommandDTO(
                cmd="demo",
                desc="演示命令",
                flags=(
                    HelpFlagDTO("-i", "不带值的开关"),
                    HelpFlagDTO("-t", "带值的开关", "秒数"),
                ),
                args="要带的内容",
            ),
            "history": HelpCommandDTO(cmd="history", desc="显示历史记录"),
        }
        for name, value in (("help_list", _MENU), ("command_specs", specs)):
            patcher = patch.object(_commands, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.reject = _commands._is_illegal_command
        self.keyword = _commands._is_single_help

    async def test_help_flag_lists(self) -> None:
        rejected, listed = await self._verdict("/demo -h")
        self.assertFalse(rejected)
        self.assertTrue(listed)

    async def test_registered_flag_with_help_lists(self) -> None:
        rejected, listed = await self._verdict("/demo -h -i")
        self.assertFalse(rejected)
        self.assertTrue(listed)

    async def test_registered_flag_alone_yields_to_command(self) -> None:
        rejected, listed = await self._verdict("/demo -i")
        self.assertFalse(rejected)
        self.assertFalse(listed)

    async def test_unregistered_flag_with_help_taken(self) -> None:
        rejected, listed = await self._verdict("/demo -h -v")
        self.assertTrue(rejected)
        self.assertFalse(listed)

    async def test_two_flags_without_help_taken(self) -> None:
        rejected, listed = await self._verdict("/demo -i -t")
        self.assertTrue(rejected)
        self.assertFalse(listed)

    async def test_repeated_registered_flag_taken(self) -> None:
        rejected, listed = await self._verdict("/demo -i -i")
        self.assertTrue(rejected)
        self.assertFalse(listed)

    async def test_value_flag_with_value_yields_to_command(self) -> None:
        rejected, listed = await self._verdict("/demo -t 5")
        self.assertFalse(rejected)
        self.assertFalse(listed)

    async def test_value_flag_without_value_taken(self) -> None:
        for text in ("/demo -t", "/demo -t -h"):
            with self.subTest(text=text):
                rejected, listed = await self._verdict(text)
                self.assertTrue(rejected)
                self.assertFalse(listed)

    async def test_value_flag_takes_next_piece_before_args(self) -> None:
        for text in ("/demo -t 5 要回显的文字", "/demo -t 要回显的文字"):
            with self.subTest(text=text):
                rejected, _ = await self._verdict(text)
                self.assertFalse(rejected)

    async def test_value_flag_with_help_lists(self) -> None:
        rejected, listed = await self._verdict("/demo -t 5 -h")
        self.assertFalse(rejected)
        self.assertTrue(listed)

    async def test_group_value_flag_without_value_taken(self) -> None:
        rejected, _ = await self._verdict("/demo -t", chat=_GROUP)
        self.assertTrue(rejected)

    async def test_trailing_text_taken_as_stray(self) -> None:
        for text in ("/history 20", "/history -h 20", "/history 20 30"):
            with self.subTest(text=text):
                rejected, listed = await self._verdict(text)
                self.assertTrue(rejected)
                self.assertFalse(listed)

    async def test_group_chat_takes_stray(self) -> None:
        for text in ("/history -h -v", "/history -i -t", "/history 20 30"):
            with self.subTest(text=text):
                rejected, listed = await self._verdict(text, chat=_GROUP)
                self.assertTrue(rejected)
                self.assertFalse(listed)

    async def test_group_help_still_lists(self) -> None:
        rejected, listed = await self._verdict("/demo -h -i", chat=_GROUP)
        self.assertFalse(rejected)
        self.assertTrue(listed)


class TestCommandMatchYield(unittest.IsolatedAsyncioTestCase):
    """命令谓词的头匹配与 -h 让行"""

    async def _hit(self, name: str, text: str) -> bool:
        message = _message(chat=_PRIVATE, text=text)
        return await CommandMatch(name)(_ctx(message))

    async def test_head_match_takes(self) -> None:
        self.assertTrue(await self._hit("history", "/history"))

    async def test_other_flag_takes(self) -> None:
        self.assertTrue(await self._hit("history", "/history -a"))

    async def test_help_flag_yields(self) -> None:
        self.assertFalse(await self._hit("history", "/history -h"))

    async def test_other_head_yields(self) -> None:
        self.assertFalse(await self._hit("history", "/demo"))


class TestAiTriggerLadder(unittest.IsolatedAsyncioTestCase):
    """AI 触发优先级"""

    def setUp(self) -> None:
        patcher = patch.object(_ai_chat, "ai_config", _StubAIConfig())
        patcher.start()
        self.addCleanup(patcher.stop)
        self.predicate = _ai_chat._triggers_chat

    async def _hit(self, message: Message) -> bool:
        return await self.predicate(_ctx(message))

    async def test_command_yields(self) -> None:
        self.assertFalse(await self._hit(_message(text="/help")))

    async def test_format_error_yields(self) -> None:
        self.assertFalse(await self._hit(_message(text="/ help")))

    async def test_mention_triggers_without_keyword(self) -> None:
        entity = MessageEntity(type="mention", offset=0, length=6)
        message = _message(text="@MyBot 在吗", entities=[entity])
        self.assertTrue(await self._hit(message))

    async def test_reply_to_bot_triggers_without_keyword(self) -> None:
        quoted = _message(id=3, text="我答过的话", from_user=_BOT)
        self.assertTrue(
            await self._hit(_message(text="接着说", reply_to_message=quoted))
        )

    async def test_keyword_is_last_fallback(self) -> None:
        self.assertTrue(await self._hit(_message(text="有个触发词 here")))

    async def test_plain_group_text_ignored(self) -> None:
        self.assertFalse(await self._hit(_message(text="随便聊聊")))

    async def test_private_text_triggers(self) -> None:
        self.assertTrue(await self._hit(_message(chat=_PRIVATE, text="随便聊聊")))

    async def test_photo_without_caption_ignored(self) -> None:
        self.assertFalse(await self._hit(_message(chat=_PRIVATE, content_type="photo")))

    async def test_photo_with_caption_triggers(self) -> None:
        """图带附文即当问话，附文归一时已换成正文"""
        self.assertTrue(
            await self._hit(
                _message(chat=_PRIVATE, content_type="photo", caption="看图")
            )
        )

    async def test_group_caption_needs_trigger(self) -> None:
        """群里的附文照走三档降级，命中触发词才答"""
        self.assertFalse(
            await self._hit(_message(content_type="photo", caption="随手一拍"))
        )
        self.assertTrue(
            await self._hit(_message(content_type="photo", caption="有个触发词"))
        )


class TestCtxReachesHandlers(unittest.IsolatedAsyncioTestCase):
    """归一上下文经完整分发链路注入"""

    def setUp(self) -> None:
        for name, value in (
            ("help_list", _MENU),
            ("generate_image", lambda: Path("help.png")),
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
        self.dispatcher.include_router(build_router(_commands.spec))

        async def run_history(raw: Message, *, ctx: HandlerContext) -> None:
            self.ran.append("history")

        other = PluginSpec(routes=(PluginRoute(CommandMatch("history"), run_history),))
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
