# devtools/tests/test_grant_access.py
"""命令权限测试

- 主人与被授权用户能用 /history 与 /clear
- 普通用户只收到无权限提示
- /grant 与 /ungrant 只主人能使，键按平台二段记
- 带 id 一步办完，不带 id 分步等下一条正文，只认发起人自己
- 待输入发 -1 即取消，非 id 的输入只重新问
"""

import asyncio
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from core.domain import ChatScope, Platform  # noqa: E402
from core.domain.ids import (  # noqa: E402
    ContainerKey,
    MessageId,
    UserId,
)
from core.dto import (  # noqa: E402
    CommandDTO,
    ContentDTO,
    InboundEventDTO,
    MsgReferenceDTO,
    OutboundPayloadDTO,
    PrincipalDTO,
)
from plugins._shared import access, grants  # noqa: E402
from plugins._shared.messages import BotMessage  # noqa: E402
from plugins.AI.handlers import _ai_chat, _history  # noqa: E402
from plugins.grant import _commands  # noqa: E402
from services.context import HandlerContext  # noqa: E402

_CONTAINER = ContainerKey("g100123")


class _Port:
    """记录外发文字的假端口"""

    def __init__(self) -> None:
        self.sent: list[str] = []

    async def send_message(
        self,
        principal: PrincipalDTO,
        content: OutboundPayloadDTO,
        *,
        mention: bool = False,
        reply_ref: MsgReferenceDTO | None = None,
    ) -> MsgReferenceDTO | None:
        self.sent.append(content.text)
        return None

    async def probe_existence(self, target: MsgReferenceDTO) -> bool:
        return True

    def mention_fragment(self, principal: PrincipalDTO) -> str:
        return ""


class _FakeRepo:
    """内存授权名单"""

    def __init__(self) -> None:
        self.rows: dict[str, str] = {}

    async def grant(self, user_key: str, granted_by: str, expires_at=None) -> bool:
        if user_key in self.rows:
            return False
        self.rows[user_key] = granted_by
        return True

    async def revoke(self, user_key: str) -> bool:
        return self.rows.pop(user_key, None) is not None

    async def contains(self, user_key: str) -> bool:
        return user_key in self.rows

    async def list_active(self) -> tuple[str, ...]:
        return tuple(self.rows)


def _ctx(
    user_id: str,
    *,
    command: CommandDTO | None = None,
    scope: ChatScope = ChatScope.GROUP,
    text: str = "/clear",
) -> tuple[HandlerContext, _Port]:
    """构造一条命令事件，默认落在群里"""
    port = _Port()
    principal = PrincipalDTO(
        platform=Platform.TELEGRAM, container=_CONTAINER, user=UserId(user_id)
    )
    ref = MsgReferenceDTO(
        platform=Platform.TELEGRAM, container=_CONTAINER, message_id=MessageId("7")
    )
    event = InboundEventDTO(
        ref=ref,
        principal=principal,
        content=ContentDTO(text=text),
        scope=scope,
        display_name="三",
        command=command or CommandDTO(matched=True, head="clear"),
    )
    return HandlerContext(event=event, interaction=port), port


def _grant_ctx(user_id: str, args: tuple[str, ...]):
    """构造一条授权命令事件"""
    return _ctx(user_id, command=CommandDTO(matched=True, head="grant", args=args))


def _admin_ctx(user_id: str, scope: ChatScope):
    """构造一条名单查询命令事件"""
    return _ctx(user_id, command=CommandDTO(matched=True, head="admin"), scope=scope)


def _text_ctx(user_id: str, text: str):
    """构造一条正文消息事件"""
    port = _Port()
    principal = PrincipalDTO(
        platform=Platform.TELEGRAM, container=_CONTAINER, user=UserId(user_id)
    )
    ref = MsgReferenceDTO(
        platform=Platform.TELEGRAM, container=_CONTAINER, message_id=MessageId("7")
    )
    event = InboundEventDTO(
        ref=ref,
        principal=principal,
        content=ContentDTO(text=text),
        scope=ChatScope.GROUP,
        display_name="三",
    )
    return HandlerContext(event=event, interaction=port), port


class AccessCase(unittest.TestCase):
    """带假名单与假主人的权限用例"""

    def setUp(self) -> None:
        self.repo = _FakeRepo()
        self.owner = "456"
        self.pending: dict[str, str] = {}

        async def _fake_repo() -> _FakeRepo:
            return self.repo

        for target, name, value in (
            (grants, "_repo", _fake_repo),
            (
                access,
                "config_manager",
                SimpleNamespace(get=lambda _p, _t: f" {self.owner} "),
            ),
            (_commands, "_pending", self.pending),
        ):
            patcher = patch.object(target, name, new=value)
            patcher.start()
            self.addCleanup(patcher.stop)

    async def _grant_user(self, target: str) -> None:
        await grants.add_admin(f"tg.{target}", "tg.g100123.456")

    def _take(self, user_id: str, text: str) -> bool:
        """判定待输入过滤器是否接管这条正文"""
        ctx, _ = _text_ctx(user_id, text)
        return asyncio.run(_commands._awaits_target(ctx))

    def _flow(self, first_args: tuple[str, ...], then: str):
        """跑完整分步流程：先发命令再发一条正文

        - 回传 (命令回执, 正文回执)
        """
        cmd_ctx, cmd_port = _grant_ctx("456", first_args)
        asyncio.run(_commands._add_grant(raw=None, ctx=cmd_ctx))
        body_ctx, body_port = _text_ctx("456", then)
        asyncio.run(_commands._finish_grant(raw=None, ctx=body_ctx))
        return cmd_port.sent, body_port.sent


class TestCommandGate(AccessCase):
    """/history 与 /clear 的门禁"""

    def setUp(self) -> None:
        super().setUp()
        self.cleared: list[str] = []

        async def _fake_clear(key: str) -> None:
            self.cleared.append(key)

        patcher = patch.object(_history, "clear_session", _fake_clear)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.records = Path(tempfile.mkdtemp())
        patcher2 = patch.object(
            _history, "ai_config", SimpleNamespace(record_dir=self.records)
        )
        patcher2.start()
        self.addCleanup(patcher2.stop)

    def test_owner_clears_db_and_record(self) -> None:
        """主人清记忆把库内上下文与记录文件一起删掉"""
        (self.records / "tg.g100123.md").write_text("正文", encoding="utf8")
        ctx, port = _ctx("456")
        asyncio.run(_history._clear_history(raw=None, ctx=ctx))

        self.assertEqual(port.sent, [BotMessage.HISTORY_MEMORY_CLEARED])
        self.assertEqual(self.cleared, ["tg.g100123"])
        self.assertFalse((self.records / "tg.g100123.md").exists())

    def test_member_is_denied(self) -> None:
        """普通用户只收到无权限"""
        ctx, port = _ctx("999")
        asyncio.run(_history._clear_history(raw=None, ctx=ctx))

        self.assertEqual(port.sent, [BotMessage.CMD_NO_PERMISSION])
        self.assertEqual(self.cleared, [])

    def test_granted_admin_can_read_history(self) -> None:
        """授权过的用户能查记录"""
        asyncio.run(self._grant_user("999"))
        (self.records / "tg.g100123.md").write_text("正文", encoding="utf8")

        ctx, port = _ctx("999")
        asyncio.run(_history._show_history(raw=None, ctx=ctx))

        self.assertEqual(port.sent[0], BotMessage.HISTORY_CAPTION)

    def test_member_cannot_read_history(self) -> None:
        """普通用户看不到记录文件"""
        ctx, port = _ctx("999")
        asyncio.run(_history._show_history(raw=None, ctx=ctx))

        self.assertEqual(port.sent, [BotMessage.CMD_NO_PERMISSION])


class TestGrantCommands(AccessCase):
    """/grant 与 /ungrant"""

    def test_owner_grants_by_id(self) -> None:
        """主人按 id 授权"""
        ctx, port = _grant_ctx("456", ("12345",))
        asyncio.run(_commands._add_grant(raw=None, ctx=ctx))

        self.assertEqual(self.repo.rows, {"tg.12345": "tg.g100123.456"})
        self.assertEqual(port.sent, [BotMessage.GRANT_ADDED.format(id="12345")])

    def test_repeat_grant_keeps_record(self) -> None:
        """重复授权提示已在名单里，流程不断"""
        asyncio.run(self._grant_user("12345"))
        ctx, port = _grant_ctx("456", ("12345",))
        asyncio.run(_commands._add_grant(raw=None, ctx=ctx))

        self.assertEqual(port.sent, [BotMessage.GRANT_EXISTS.format(id="12345")])
        self.assertEqual(self.pending, {"tg.g100123.456": _commands._GrantStep.ADD})

    def test_grant_without_arg_asks_target(self) -> None:
        """缺参数即提问并挂起待输入"""
        ctx, port = _grant_ctx("456", ())
        asyncio.run(_commands._add_grant(raw=None, ctx=ctx))

        self.assertEqual(port.sent, [BotMessage.GRANT_ASK_TARGET])
        self.assertEqual(self.pending, {"tg.g100123.456": _commands._GrantStep.ADD})
        self.assertEqual(self.repo.rows, {})

    def test_grant_with_two_args_shows_usage(self) -> None:
        """参数多于一个只报用法，不挂待输入"""
        ctx, port = _grant_ctx("456", ("12345", "67890"))
        asyncio.run(_commands._add_grant(raw=None, ctx=ctx))

        self.assertEqual(port.sent, [BotMessage.GRANT_USAGE])
        self.assertEqual(self.pending, {})
        self.assertEqual(self.repo.rows, {})

    def test_admin_cannot_grant(self) -> None:
        """管理员不能再授权别人"""
        asyncio.run(self._grant_user("999"))
        ctx, port = _grant_ctx("999", ("777",))
        asyncio.run(_commands._add_grant(raw=None, ctx=ctx))

        self.assertEqual(port.sent, [BotMessage.CMD_NO_PERMISSION])
        self.assertEqual(self.repo.rows, {"tg.999": "tg.g100123.456"})

    def test_owner_revokes(self) -> None:
        """主人撤销后名单里没了"""
        asyncio.run(self._grant_user("12345"))
        ctx, port = _ctx(
            "456", command=CommandDTO(matched=True, head="ungrant", args=("12345",))
        )
        asyncio.run(_commands._drop_grant(raw=None, ctx=ctx))

        self.assertEqual(self.repo.rows, {})
        self.assertEqual(port.sent, [BotMessage.UNGRANT_REMOVED.format(id="12345")])

    def test_revoke_unknown_id(self) -> None:
        """撤销不在名单里的 id，提示后继续等重发"""
        ctx, port = _ctx(
            "456", command=CommandDTO(matched=True, head="ungrant", args=("777",))
        )
        asyncio.run(_commands._drop_grant(raw=None, ctx=ctx))

        self.assertEqual(port.sent, [BotMessage.UNGRANT_MISSING.format(id="777")])
        self.assertEqual(self.pending, {"tg.g100123.456": _commands._GrantStep.DROP})


class TestWriteFailure(AccessCase):
    """名单写不进时不终止流程"""

    async def _boom(self, *_args, **_kwargs):
        raise RuntimeError("库写不进")

    def test_retry_hint_keeps_the_flow(self) -> None:
        """直带 id 写失败只提示重试，待输入挂着"""
        with patch.object(_commands, "add_admin", self._boom):
            ctx, port = _grant_ctx("456", ("12345",))
            asyncio.run(_commands._add_grant(raw=None, ctx=ctx))

        self.assertEqual(port.sent, [BotMessage.GRANT_RETRY_TARGET])
        self.assertEqual(self.pending, {"tg.g100123.456": _commands._GrantStep.ADD})

    def test_stepwise_retry_then_success(self) -> None:
        """分步里先写失败、再发同一条 id 即办成"""
        asked, replied = self._flow((), "12345")
        self.assertEqual(asked, [BotMessage.GRANT_ASK_TARGET])
        self.assertEqual(replied, [BotMessage.GRANT_ADDED.format(id="12345")])

        self.pending.clear()
        self.repo.rows.clear()
        with patch.object(_commands, "add_admin", self._boom):
            ctx, _ = _grant_ctx("456", ())
            asyncio.run(_commands._add_grant(raw=None, ctx=ctx))
            body_ctx, body_port = _text_ctx("456", "999")
            asyncio.run(_commands._finish_grant(raw=None, ctx=body_ctx))

        self.assertEqual(body_port.sent, [BotMessage.GRANT_RETRY_TARGET])
        self.assertEqual(self.pending, {"tg.g100123.456": _commands._GrantStep.ADD})


class TestGrantStepwise(AccessCase):
    """不带 id 时分步授权"""

    def test_target_id_completes_grant(self) -> None:
        """随后单发一条 id 即完成授权"""
        asked, replied = self._flow((), "12345")

        self.assertEqual(asked, [BotMessage.GRANT_ASK_TARGET])
        self.assertEqual(replied, [BotMessage.GRANT_ADDED.format(id="12345")])
        self.assertEqual(self.repo.rows, {"tg.12345": "tg.g100123.456"})
        self.assertEqual(self.pending, {})

    def test_only_initiator_is_taken(self) -> None:
        """别人的正文不接管，也不误伤流程"""
        self._flow((), "占位")
        self.assertFalse(self._take("999", "12345"))
        self.assertTrue(self._take("456", "12345"))

    def test_command_message_is_not_taken(self) -> None:
        """流程挂起期间发的命令不被当目标吞掉"""
        self._flow((), "占位")
        ctx, _ = _ctx("456")

        self.assertFalse(asyncio.run(_commands._awaits_target(ctx)))

    def test_bad_target_asks_again(self) -> None:
        """输的不是 id 就重新问，流程不断"""
        asked, replied = self._flow((), "张三")

        self.assertEqual(asked, [BotMessage.GRANT_ASK_TARGET])
        self.assertEqual(replied, [BotMessage.GRANT_BAD_TARGET])
        self.assertEqual(self.pending, {"tg.g100123.456": _commands._GrantStep.ADD})
        self.assertEqual(self.repo.rows, {})

    def test_minus_one_cancels_the_flow(self) -> None:
        """发 -1 即中止流程，名单不动"""
        _, replied = self._flow((), "-1")

        self.assertEqual(replied, [BotMessage.GRANT_CANCELED])
        self.assertEqual(self.pending, {})
        self.assertEqual(self.repo.rows, {})

    def test_zero_and_word_are_not_ids(self) -> None:
        """0 与 stop 都不是取消词也不是 id，只重新问"""
        for word in ("0", "stop"):
            with self.subTest(word=word):
                self.pending.clear()
                self.repo.rows.clear()
                _, replied = self._flow((), word)

                self.assertEqual(replied, [BotMessage.GRANT_BAD_TARGET])
                self.assertEqual(
                    self.pending, {"tg.g100123.456": _commands._GrantStep.ADD}
                )
                self.assertEqual(self.repo.rows, {})

    def test_ungrant_flow(self) -> None:
        """撤销走同一套分步"""
        asyncio.run(self._grant_user("12345"))
        ctx, port = _ctx("456", command=CommandDTO(matched=True, head="ungrant"))
        asyncio.run(_commands._drop_grant(raw=None, ctx=ctx))
        self.assertEqual(port.sent, [BotMessage.UNGRANT_ASK_TARGET])

        body_ctx, body_port = _text_ctx("456", "12345")
        asyncio.run(_commands._finish_grant(raw=None, ctx=body_ctx))

        self.assertEqual(
            body_port.sent, [BotMessage.UNGRANT_REMOVED.format(id="12345")]
        )
        self.assertEqual(self.repo.rows, {})
        self.assertEqual(self.pending, {})

    def test_reissue_switches_the_flow(self) -> None:
        """流程中再发另一条命令即改认的目标动作"""
        self._flow((), "占位")
        ctx, port = _ctx("456", command=CommandDTO(matched=True, head="ungrant"))
        asyncio.run(_commands._drop_grant(raw=None, ctx=ctx))

        self.assertEqual(port.sent, [BotMessage.UNGRANT_ASK_TARGET])
        self.assertEqual(self.pending, {"tg.g100123.456": _commands._GrantStep.DROP})

    def test_member_cannot_start_the_flow(self) -> None:
        """非主人连流程都起不来"""
        ctx, port = _grant_ctx("999", ())
        asyncio.run(_commands._add_grant(raw=None, ctx=ctx))

        self.assertEqual(port.sent, [BotMessage.CMD_NO_PERMISSION])
        self.assertEqual(self.pending, {})

    def test_empty_text_is_not_taken(self) -> None:
        """没正文的消息不当目标"""
        self._flow((), "占位")

        self.assertFalse(self._take("456", ""))
        self.assertEqual(self.pending, {"tg.g100123.456": _commands._GrantStep.ADD})


class TestPrivateGate(AccessCase):
    """私聊场景要管理员以上"""

    def setUp(self) -> None:
        super().setUp()
        self.gate = _ai_chat._denied_private

    def _taken(
        self,
        user_id: str,
        *,
        text: str = "随便一句",
        command: CommandDTO | None = None,
        scope: ChatScope = ChatScope.PRIVATE,
    ) -> bool:
        ctx, _ = _ctx(user_id, command=command or CommandDTO(), scope=scope, text=text)
        return asyncio.run(self.gate(ctx))

    def test_member_private_is_taken(self) -> None:
        """成员在私聊发的普通文本被门槛接走"""
        self.assertTrue(self._taken("999"))

    def test_member_gets_one_denial(self) -> None:
        """接走只回一句门槛说明，不入队"""
        ctx, port = _ctx("999")
        asyncio.run(_ai_chat._deny_private(raw=None, ctx=ctx))
        self.assertEqual(port.sent, [BotMessage.CHAT_PRIVATE_DENIED])

    def test_admin_and_owner_pass(self) -> None:
        """授权过的人与主人都放行到对话"""
        asyncio.run(self._grant_user("999"))
        self.assertFalse(self._taken("999"))
        self.assertFalse(self._taken("456"))

    def test_group_member_passes(self) -> None:
        """群里不拦成员的基础对话"""
        self.assertFalse(self._taken("999", scope=ChatScope.GROUP))

    def test_command_is_not_taken(self) -> None:
        """命令交给各自的档位判定"""
        self.assertFalse(
            self._taken("999", command=CommandDTO(matched=True, head="help"))
        )

    def test_empty_text_is_not_taken(self) -> None:
        """没有正文的消息不当门槛对象"""
        self.assertFalse(self._taken("999", text=""))


class TestAdminView(AccessCase):
    """/admin 查授权名单"""

    def _ask(
        self, user_id: str = "456", scope: ChatScope = ChatScope.PRIVATE
    ) -> list[str]:
        """发一条查询并交出回执"""
        ctx, port = _admin_ctx(user_id, scope)
        asyncio.run(_commands._show_admins(raw=None, ctx=ctx))
        return port.sent

    def test_private_lists_each_key(self) -> None:
        """私聊逐条列出二段键"""
        asyncio.run(self._grant_user("777"))
        asyncio.run(self._grant_user("888"))

        self.assertEqual(
            self._ask(),
            [BotMessage.ADMIN_LIST.format(count=2, ids="- tg.777\n- tg.888")],
        )

    def test_group_reports_count_only(self) -> None:
        """群里只回条数，名单不外泄"""
        asyncio.run(self._grant_user("777"))

        self.assertEqual(
            self._ask(scope=ChatScope.GROUP), [BotMessage.ADMIN_COUNT.format(count=1)]
        )

    def test_empty_list_answers_once(self) -> None:
        """名单为空时两种场景同一句"""
        self.assertEqual(self._ask(), [BotMessage.ADMIN_EMPTY])
        self.assertEqual(self._ask(scope=ChatScope.GROUP), [BotMessage.ADMIN_EMPTY])

    def test_admin_cannot_look(self) -> None:
        """管理员档看不到名单，只有主人能使"""
        asyncio.run(self._grant_user("999"))

        self.assertEqual(self._ask("999"), [BotMessage.CMD_NO_PERMISSION])


class TestUserKey(unittest.TestCase):
    """授权用的二段键"""

    def test_user_key_drops_container(self) -> None:
        """二段键不含容器段"""
        principal = PrincipalDTO(
            platform=Platform.TELEGRAM, container=_CONTAINER, user=UserId("456")
        )
        self.assertEqual(principal.user_key, "tg.456")
        self.assertEqual(principal.key, "tg.g100123.456")


if __name__ == "__main__":
    unittest.main()
