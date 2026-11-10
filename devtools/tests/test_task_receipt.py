# devtools/tests/test_task_receipt.py
"""停机交代测试

- 真库往返，替身外发端口只记收到哪一句
- 没欠账即一句不说，也不判死
- 补说按会话收口：同一会话多人欠账只补一句，收件人取首个欠答者
- 配置填了话术即随机取一句，整表空即交模型现写，现写也只按会话各跑一次
- 现写一次给几句候选，行首编号与引号洗掉、长过一句交代的量即不算候选
- 现写的指令并进人设那条系统轮，用户轮只留一句让它开口
- 同一次启动里几个会话各补一句时，说过的候选不再取
- 送不出去与现写失败照常判死，防下次启动重说一遍
"""

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from bundled.AI.config import ai_config  # noqa: E402
from bundled.AI.services import _receipt  # noqa: E402
from bundled.AI.services._receipt import report_lost_tasks  # noqa: E402
from data import (  # noqa: E402
    build_repositories,
    close_all,
    get_connection,
    run_migrations,
)
from finshin_sdk import CapabilityCall  # noqa: E402
from finshin_sdk.domain import (  # noqa: E402
    Platform,
    TaskStatus,
)
from finshin_sdk.domain.ids import (  # noqa: E402
    KEY_SEP,
    ContainerKey,
    MessageId,
    TaskId,
    UserId,
)
from finshin_sdk.dto import (  # noqa: E402
    MsgReferenceDTO,
    PrincipalDTO,
    TaskPatchDTO,
    TaskRequestDTO,
)
from utils import config_manager  # noqa: E402


class _FakeSayer:
    """只记录说出去的话

    - raise_on 点名某个用户 id，发给他的那一句当场抛
    """

    def __init__(self, *, raise_on: str = "") -> None:
        self.sent: list[tuple[str, str]] = []
        self._raise_on = raise_on

    @property
    def call(self) -> CapabilityCall:
        """平台交出去的那份交代，说话这一路换成记录"""
        return CapabilityCall(say=self._say)

    async def _say(self, principal: PrincipalDTO, text: str) -> None:
        if self._raise_on and self._raise_on in principal.user:
            raise ConnectionError("送不出去")
        self.sent.append((principal.key, text))


def _fake_client(*, reply: str = "", fail: bool = False):
    """替身模型客户端，回话分两段流出

    - 返回客户端与它收到的请求列表
    - fail 为真即请求当场抛
    """
    seen: list = []

    async def stream_chat(msg, usage=None):
        seen.append(msg)
        if fail:
            raise ConnectionError("模型没通")
        yield {"content": reply[:6]}
        yield {"content": reply[6:]}

    return SimpleNamespace(stream_chat=stream_chat), seen


def _principal(user: str, container: str = "g100123") -> PrincipalDTO:
    """构造测试主体"""
    return PrincipalDTO(
        platform=Platform.TELEGRAM,
        container=ContainerKey(container),
        user=UserId(user),
    )


def _chat_id(principal: PrincipalDTO) -> TaskId:
    """取该主体的问答任务行号"""
    return TaskId(f"{principal.key}{KEY_SEP}demo.chat")


class TestReportLostTasks(unittest.IsolatedAsyncioTestCase):
    """重启时补那一句"""

    async def asyncSetUp(self) -> None:
        tmp = tempfile.TemporaryDirectory(prefix="finshin-receipt-")
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        self.db = root / "bot.db"
        (root / "backups").mkdir()
        conn = await get_connection(self.db)
        await run_migrations(conn, self.db, root / "backups")
        self.addAsyncCleanup(close_all)
        self.repos = build_repositories(conn)

        patcher = patch.object(_receipt, "DB_FILE", self.db)
        patcher.start()
        self.addCleanup(patcher.stop)

        self.cfg = SimpleNamespace(
            lost_lines=("甲句", "乙句"),
            init=({"role": "system", "content": "人设正文"},),
        )
        patcher = patch.object(_receipt, "ai_config", self.cfg)
        patcher.start()
        self.addCleanup(patcher.stop)

    async def _owe(
        self, user: str, *, running: bool = False, container: str = "g100123"
    ) -> None:
        """给该主体留一行欠账"""
        principal = _principal(user, container)
        await self.repos.principal.upsert(principal, "张三")
        await self.repos.task.insert(
            TaskRequestDTO(
                principal=principal,
                kind="demo.chat",
                source_ref=MsgReferenceDTO(
                    platform=principal.platform,
                    container=principal.container,
                    message_id=MessageId("789"),
                ),
            )
        )
        if running:
            await self.repos.task.patch(
                _chat_id(principal), TaskPatchDTO(status=TaskStatus.RUNNING)
            )

    async def test_no_debt_says_nothing(self) -> None:
        """库里干净即一句不说"""
        sayer = _FakeSayer()

        await report_lost_tasks(sayer.call)

        self.assertEqual(sayer.sent, [])

    async def test_same_container_shares_one_line(self) -> None:
        """同群两人各欠一串，只补一句，收件人是先记上的那位"""
        await self._owe("111")
        await self._owe("222", running=True)
        sayer = _FakeSayer()

        await report_lost_tasks(sayer.call)

        self.assertEqual(len(sayer.sent), 1)
        self.assertEqual(sayer.sent[0][0], _principal("111").key)
        self.assertIn(sayer.sent[0][1], self.cfg.lost_lines)
        self.assertEqual(await self.repos.task.list_all_unfinished(), ())

    async def test_each_container_gets_a_line(self) -> None:
        """两个会话各欠一串，各补一句"""
        await self._owe("111")
        await self._owe("222", running=True, container="g200456")
        sayer = _FakeSayer()

        await report_lost_tasks(sayer.call)

        self.assertEqual(
            [key for key, _ in sayer.sent],
            [_principal("111").key, _principal("222", "g200456").key],
        )
        for _, text in sayer.sent:
            self.assertIn(text, self.cfg.lost_lines)

    async def test_empty_config_lets_model_write(self) -> None:
        """话术留空即交模型现写候选，洗掉编号与引号后随机取一句发出"""
        await self._owe("111")
        await self._owe("222")
        self.cfg.lost_lines = ()
        client, seen = _fake_client(
            reply=(
                "1. **刚才我睡过去了**，现在我在呢\n"
                "2. 「我在看草，这就回来啦」\n"
                "3. 刚才不在，现在在呢"
            )
        )
        sayer = _FakeSayer()

        with patch.object(_receipt, "AIClient", client):
            await report_lost_tasks(sayer.call)

        self.assertEqual(len(seen), 1)
        self.assertEqual([key for key, _ in sayer.sent], [_principal("111").key])
        self.assertIn(
            sayer.sent[0][1],
            (
                "刚才我睡过去了，现在我在呢",
                "我在看草，这就回来啦",
                "刚才不在，现在在呢",
            ),
        )
        self.assertEqual(seen[0][0]["role"], "system")
        self.assertIn("人设正文", seen[0][0]["content"])
        self.assertIn("每句只说自己回来了", seen[0][0]["content"])
        self.assertIn("不讲刚才去了哪里、做了什么", seen[0][0]["content"])
        self.assertIn("不提程序、断线与故障", seen[0][0]["content"])
        self.assertEqual(seen[0][1], {"role": "user", "content": "把这几句直接说出来"})
        self.assertEqual(await self.repos.task.list_all_unfinished(), ())

    async def test_candidates_not_reused_across_containers(self) -> None:
        """两个会话各跑一次现写，候选说过的不再重复取"""
        await self._owe("111")
        await self._owe("222", running=True, container="g200456")
        self.cfg.lost_lines = ()
        client, seen = _fake_client(reply="甲句\n乙句")
        sayer = _FakeSayer()

        with patch.object(_receipt, "AIClient", client):
            await report_lost_tasks(sayer.call)

        self.assertEqual(len(seen), 2)
        self.assertEqual({text for _, text in sayer.sent}, {"甲句", "乙句"})

    async def test_compose_failure_still_marks_dead(self) -> None:
        """模型没通即那句不说，照常判死"""
        await self._owe("111")
        self.cfg.lost_lines = ()
        client, _ = _fake_client(fail=True)
        sayer = _FakeSayer()

        with patch.object(_receipt, "AIClient", client):
            await report_lost_tasks(sayer.call)

        self.assertEqual(sayer.sent, [])
        dead = await self.repos.task.find(_chat_id(_principal("111")))
        assert dead is not None
        self.assertEqual(dead.status, TaskStatus.FAILED)

    async def test_send_failure_still_marks_dead(self) -> None:
        """送不出去也判死，下次启动不重说"""
        await self._owe("111")
        sayer = _FakeSayer(raise_on="111")

        await report_lost_tasks(sayer.call)

        self.assertEqual(sayer.sent, [])
        dead = await self.repos.task.find(_chat_id(_principal("111")))
        assert dead is not None
        self.assertEqual(dead.status, TaskStatus.FAILED)


class TestCandidateSplit(unittest.TestCase):
    """候选拆行的清洗"""

    def test_overlong_line_dropped(self) -> None:
        """长过一句交代的量即不算候选，拒答与铺陈整段就此丢掉"""
        short = "刚才不在，现在回来啦"
        overlong = "整段拒答的说明会一直写下去，" * 20
        self.assertEqual(_receipt._split_candidates(f"{short}\n{overlong}"), [short])


class TestLostLinesConfig(unittest.TestCase):
    """交代话术读配置的回归点

    - 只填了空白的条目即没填
    """

    def _read(self, value: list[str]) -> tuple[str, ...]:
        """把配置中心的这一项读成话术元组"""
        with patch.object(config_manager, "get", lambda _path, _type: value):
            return ai_config.lost_lines

    def test_blank_entries_dropped(self) -> None:
        """留白的那几条不进话术"""
        self.assertEqual(self._read(["有字的一句", "  ", ""]), ("有字的一句",))

    def test_all_blank_gives_empty(self) -> None:
        """整表空白即空元组，运行期走现写"""
        self.assertEqual(self._read(["", "   "]), ())


if __name__ == "__main__":
    unittest.main(verbosity=2)
