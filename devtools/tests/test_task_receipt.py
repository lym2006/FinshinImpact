# devtools/tests/test_task_receipt.py
"""停机交代测试

- 真库往返，替身外发端口只记收到哪一句
- 没欠账即一句不说，也不判死
- 有欠账逐行各说一句，句式轮换，说完整批判死
- 送不出去照常判死，防下次启动重说一遍
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from core.domain import (  # noqa: E402
    Platform,
    TaskKind,
    TaskPriority,
    TaskStatus,
)
from core.domain.ids import (  # noqa: E402
    KEY_SEP,
    ContainerKey,
    MessageId,
    TaskId,
    UserId,
)
from core.dto import (  # noqa: E402
    MsgReferenceDTO,
    OutboundPayloadDTO,
    PrincipalDTO,
    TaskPatchDTO,
    TaskRequestDTO,
)
from data import (  # noqa: E402
    build_repositories,
    close_all,
    get_connection,
    run_migrations,
)
from plugins._shared.messages import BotMessage  # noqa: E402
from plugins.AI.services import _receipt  # noqa: E402
from plugins.AI.services._receipt import report_lost_tasks  # noqa: E402


class _FakeInteraction:
    """只记录发出的外发端口

    - raise_on 点名某个用户 id，发给他的那一句当场抛
    """

    def __init__(self, *, raise_on: str = "") -> None:
        self.sent: list[tuple[str, str]] = []
        self._raise_on = raise_on

    async def send_message(
        self, principal: PrincipalDTO, content: OutboundPayloadDTO
    ) -> None:
        if self._raise_on and self._raise_on in principal.user:
            raise ConnectionError("送不出去")
        self.sent.append((principal.key, content.text))


def _principal(user: str) -> PrincipalDTO:
    """构造测试主体"""
    return PrincipalDTO(
        platform=Platform.TELEGRAM,
        container=ContainerKey("g100123"),
        user=UserId(user),
    )


def _chat_id(principal: PrincipalDTO) -> TaskId:
    """取该主体的问答任务行号"""
    return TaskId(f"{principal.key}{KEY_SEP}{TaskKind.CHAT}")


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

    async def _owe(self, user: str, *, running: bool = False) -> None:
        """给该主体留一行欠账"""
        principal = _principal(user)
        await self.repos.principal.upsert(principal, "张三")
        await self.repos.task.insert(
            TaskRequestDTO(
                principal=principal,
                kind=TaskKind.CHAT,
                source_ref=MsgReferenceDTO(
                    platform=principal.platform,
                    container=principal.container,
                    message_id=MessageId("789"),
                ),
                priority=TaskPriority.NORMAL,
            )
        )
        if running:
            await self.repos.task.patch(
                _chat_id(principal), TaskPatchDTO(status=TaskStatus.RUNNING)
            )

    async def test_no_debt_says_nothing(self) -> None:
        """库里干净即一句不说"""
        interaction = _FakeInteraction()

        await report_lost_tasks(interaction)  # type: ignore[arg-type]

        self.assertEqual(interaction.sent, [])

    async def test_each_debt_row_gets_one_rotating_line(self) -> None:
        """两个主体各说一句，句式轮换不重样"""
        await self._owe("111")
        await self._owe("222", running=True)
        interaction = _FakeInteraction()

        await report_lost_tasks(interaction)  # type: ignore[arg-type]

        self.assertEqual(
            interaction.sent,
            [
                (_principal("111").key, BotMessage.CHAT_LOST_SLEEP),
                (_principal("222").key, BotMessage.CHAT_LOST_LINK),
            ],
        )
        self.assertEqual(await self.repos.task.list_all_unfinished(), ())

    async def test_send_failure_still_marks_dead(self) -> None:
        """送不出去也判死，下次启动不重说"""
        await self._owe("111")
        interaction = _FakeInteraction(raise_on="111")

        await report_lost_tasks(interaction)  # type: ignore[arg-type]

        self.assertEqual(interaction.sent, [])
        dead = await self.repos.task.find(_chat_id(_principal("111")))
        assert dead is not None
        self.assertEqual(dead.status, TaskStatus.FAILED)


if __name__ == "__main__":
    unittest.main(verbosity=2)
