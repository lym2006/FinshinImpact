"""命令路由样例测试

- 覆盖帮助插件的形态回执与 AI 触发优先级
"""

import sys
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from utils import config_manager  # noqa: E402

_AI_SEED = {
    "chore.owner": "456",
    "chore.triggers": ["触发词"],
}

with patch.object(config_manager, "get", lambda path, _type: _AI_SEED[path]):
    from bundled.AI.handlers import _ai_chat  # noqa: E402

from inbound_events import Chat as _Chat  # noqa: E402
from inbound_events import Msg as _Msg  # noqa: E402
from inbound_events import User as _User  # noqa: E402
from inbound_events import event as _event  # noqa: E402
from inbound_events import message  # noqa: E402

from bundled._shared.filters import CommandMatch  # noqa: E402
from bundled.help import _commands  # noqa: E402
from finshin_sdk import HandlerContext  # noqa: E402
from finshin_sdk.dto import (  # noqa: E402
    HelpCommandDTO,
    HelpFlagDTO,
    MsgReferenceDTO,
    OutboundPayloadDTO,
)

_GROUP = _Chat(id=-100123, type="supergroup", title="测试群")
_PRIVATE = _Chat(id=456, type="private")
_CHANNEL = _Chat(id=-100999, type="channel", title="测试频道")
_USER = _User(id=456, full_name="三")
_BOT = _User(id=777, full_name="机器人", username="MyBot")

# 参与判定的菜单项，与实例启用集解耦
_MENU = {
    "help": "帮助",
    "history": "显示历史记录",
    "demo": "演示命令",
}


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


def _message(chat: _Chat = _GROUP, **fields: Any) -> _Msg:
    """构造一条消息，发言人默认是群友"""
    fields.setdefault("sender", _USER)
    return message(chat, **fields)


def _ctx(msg: _Msg) -> HandlerContext:
    """组一条带归一事件的上下文"""
    return HandlerContext(
        event=_event(msg, bot=_BOT), interaction=_RecordingInteraction()
    )


class _VerdictMixin:
    """回执与单命令帮助的双标记判定"""

    reject: Any
    keyword: Any

    async def _verdict(self, text: str, chat: _Chat = _PRIVATE) -> tuple[bool, bool]:
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
                    HelpFlagDTO("-t", "带值的开关", 0.0),
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
                self.assertTrue(rejected)

    async def test_pieces_before_flags_are_args(self) -> None:
        for text in ("/demo 要回显的文字", "/demo 要回显 的 文字 -t 5"):
            with self.subTest(text=text):
                rejected, listed = await self._verdict(text)
                self.assertFalse(rejected)
                self.assertFalse(listed)

    async def test_several_value_flags_yield(self) -> None:
        rejected, listed = await self._verdict("/demo -i -t 5 -h")
        self.assertFalse(rejected)
        self.assertTrue(listed)

    async def test_value_out_of_default_type_taken(self) -> None:
        rejected, _ = await self._verdict("/demo -t 甲")
        self.assertTrue(rejected)

    async def test_decimal_input_yields_to_command(self) -> None:
        rejected, listed = await self._verdict("/demo -t 2.5")
        self.assertFalse(rejected)
        self.assertFalse(listed)

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

    async def _hit(self, message: _Msg) -> bool:
        return await self.predicate(_ctx(message))

    async def test_command_yields(self) -> None:
        self.assertFalse(await self._hit(_message(text="/help")))

    async def test_format_error_yields(self) -> None:
        self.assertFalse(await self._hit(_message(text="/ help")))

    async def test_mention_triggers_without_keyword(self) -> None:
        message = _message(text="@MyBot 在吗", mentions_bot=True)
        self.assertTrue(await self._hit(message))

    async def test_reply_to_bot_triggers_without_keyword(self) -> None:
        quoted = _message(id=3, text="我答过的话", sender=_BOT)
        self.assertTrue(await self._hit(_message(text="接着说", quoted=quoted)))

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


if __name__ == "__main__":
    unittest.main()
