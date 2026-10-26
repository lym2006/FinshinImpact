# devtools/tests/test_data_layer.py
"""data 层真库测试

- 建表、版本行与 WAL 外键一次验完
- 主体、会话、任务、授权、媒体索引逐条往返
- 迁移重跑幂等、备份只留三份、高版本拒读、启动清死行同批查
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

import aiosqlite  # noqa: E402

from core.domain import (  # noqa: E402
    ChatRole,
    ContentKind,
    Platform,
    TaskKind,
    TaskPayload,
    TaskPriority,
    TaskStatus,
)
from core.domain.ids import (  # noqa: E402
    ContainerKey,
    MessageId,
    PrincipalKey,
    SessionKey,
    TaskId,
    UserId,
)
from core.dto import (  # noqa: E402
    MediaEntryDTO,
    MessageDTO,
    MsgReferenceDTO,
    PrincipalDTO,
    SessionDTO,
    SessionPatchDTO,
    TaskPatchDTO,
    TaskRequestDTO,
)
from data import (  # noqa: E402
    build_repositories,
    check_schema_compatible,
    close_all,
    get_connection,
    purge_dead_tasks,
    run_migrations,
)

# 闲置判定样本时刻（秒），只用于比对清除界限
_STALE_AT = 1.0
_LIVE_AT = 9.0
_DEADLINE = 5.0

# 任务载荷样本，读回时按整串比对
_CHAT_PAYLOAD: TaskPayload = ((ChatRole.USER, "同一句话"),)

# 建表后 sqlite_master 里该有的名字
_EXPECTED_OBJECTS = frozenset(
    {
        "principal",
        "session",
        "session_message",
        "group_message",
        "task",
        "media_asset",
        "grant",
        "schema_version",
        "idx_task_dedupe",
        "idx_message_seq",
        "idx_groupmsg_msg",
        "idx_media_container",
    }
)


def _principal(group: bool = True) -> PrincipalDTO:
    """构造测试主体"""
    return PrincipalDTO(
        platform=Platform.TELEGRAM,
        container=ContainerKey("g100123" if group else "u456"),
        user=UserId("456"),
    )


def _ref() -> MsgReferenceDTO:
    """构造测试消息定位"""
    return MsgReferenceDTO(
        platform=Platform.TELEGRAM,
        container=ContainerKey("g100123"),
        message_id=MessageId("789"),
    )


def _session_key() -> SessionKey:
    """取测试会话键"""
    return SessionKey(f"{Platform.TELEGRAM}.g100123")


def _empty_session() -> SessionDTO:
    """构造空会话快照供比对"""
    return SessionDTO(platform=Platform.TELEGRAM, container=ContainerKey("g100123"))


async def _one(conn: aiosqlite.Connection, sql: str, *params: object) -> aiosqlite.Row:
    """取单行查询结果

    - 空结果当场断言失败，免得空行渗进后续比对
    """
    async with conn.execute(sql, params) as cursor:
        row = await cursor.fetchone()
    assert row is not None, sql
    return row


def _contents(session: SessionDTO) -> list[str]:
    """取会话消息正文序列供比对"""
    return [message.content for message in session.messages]


class _RealDb(unittest.IsolatedAsyncioTestCase):
    """每例各开一只临时库

    - 建库即跑迁移，仓储按需装配
    - 收尾先合并 WAL 关连接，再删临时目录
    """

    async def asyncSetUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="finshin-data-")
        self.root = Path(self.tmp.name)
        self.db = self.root / "bot.db"
        self.backup_dir = self.root / "backups"
        self.backup_dir.mkdir()
        self.addCleanup(self.tmp.cleanup)
        self.addAsyncCleanup(close_all)
        self.conn = await get_connection(self.db)
        await run_migrations(self.conn, self.db, self.backup_dir)
        self.repos = build_repositories(self.conn)


class TestSchema(_RealDb):
    """建表、版本行与连接参数"""

    async def test_tables_and_pragmas(self) -> None:
        """表与索引齐、版本落一行、WAL 与外键已开"""
        async with self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table','index')"
        ) as cursor:
            names = {row["name"] for row in await cursor.fetchall()}
        async with self.conn.execute(
            "SELECT version, checksum FROM schema_version"
        ) as cursor:
            rows = list(await cursor.fetchall())

        self.assertLessEqual(_EXPECTED_OBJECTS, names)
        self.assertEqual([row["version"] for row in rows], [1])
        self.assertTrue(rows[0]["checksum"])
        self.assertEqual((await _one(self.conn, "PRAGMA journal_mode"))[0], "wal")
        self.assertEqual((await _one(self.conn, "PRAGMA foreign_keys"))[0], 1)

    async def test_rerun_is_idempotent(self) -> None:
        """整库删净重跑，对象数与版本行一致"""
        before = (await _one(self.conn, "SELECT COUNT(*) FROM sqlite_master"))[0]
        await close_all()

        for leftover in self.root.glob("bot.db*"):
            leftover.unlink()
        self.conn = await get_connection(self.db)
        await run_migrations(self.conn, self.db, self.backup_dir)

        after = (await _one(self.conn, "SELECT COUNT(*) FROM sqlite_master"))[0]
        self.assertEqual(before, after)
        versions = await _one(self.conn, "SELECT COUNT(*) FROM schema_version")
        self.assertEqual(versions[0], 1)

    async def test_backup_keeps_three(self) -> None:
        """重跑迁移四次只留三份备份"""
        for _ in range(4):
            await self.conn.execute("DELETE FROM schema_version")
            await self.conn.commit()
            await run_migrations(self.conn, self.db, self.backup_dir)

        self.assertEqual(len(sorted(self.backup_dir.glob("bot-*.db"))), 3)

    async def test_higher_version_is_rejected(self) -> None:
        """库版本高于支持即拒读，改回本版本可读"""
        await self.conn.execute("UPDATE schema_version SET version = 999")
        await self.conn.commit()
        self.assertFalse(await check_schema_compatible(self.conn))

        await self.conn.execute("UPDATE schema_version SET version = 1")
        await self.conn.commit()
        self.assertTrue(await check_schema_compatible(self.conn))


class TestPrincipal(_RealDb):
    """主体读写往返"""

    async def test_upsert_then_find(self) -> None:
        """原样存回、按键取回、缺行返回空"""
        principal = _principal()

        self.assertEqual(
            await self.repos.principal.upsert(principal, "张三"), principal
        )
        self.assertEqual(
            await self.repos.principal.find_by_key(principal.key), principal
        )
        self.assertIsNone(
            await self.repos.principal.find_by_key(PrincipalKey("tg.g1.9"))
        )

    async def test_display_name_is_overwritten(self) -> None:
        """同一主体重复登记只盖展示名"""
        principal = _principal()
        await self.repos.principal.upsert(principal, "张三")

        await self.repos.principal.upsert(principal, "李四")

        row = await _one(
            self.conn, "SELECT display_name FROM principal WHERE key = ?", principal.key
        )
        self.assertEqual(row[0], "李四")


class TestSession(_RealDb):
    """会话追加、限量、重置与四条清除"""

    async def test_load_missing_returns_empty(self) -> None:
        """库里没这串即空快照，不报错"""
        self.assertEqual(
            await self.repos.session.load(_session_key()), _empty_session()
        )

    async def test_append_and_summary(self) -> None:
        """追加问答带上发言人，摘要同写入"""
        key = _session_key()

        patched = await self.repos.session.apply_patch(
            key,
            SessionPatchDTO(
                append=(
                    MessageDTO(
                        role=ChatRole.USER,
                        content="你好",
                        created_at=1.0,
                        sender_id="456",
                        sender_name="张三",
                    ),
                    MessageDTO(role=ChatRole.ASSISTANT, content="在的", created_at=2.0),
                ),
                summary="摘要一",
            ),
        )

        self.assertEqual(_contents(patched), ["你好", "在的"])
        self.assertEqual(patched.messages[0].sender_id, "456")
        self.assertEqual(patched.messages[0].sender_name, "张三")
        self.assertEqual(patched.summary, "摘要一")

    async def test_limit_takes_tail(self) -> None:
        """限量只取最末几条"""
        key = _session_key()
        await self.repos.session.apply_patch(
            key,
            SessionPatchDTO(
                append=(
                    MessageDTO(role=ChatRole.USER, content="你好", created_at=1.0),
                    MessageDTO(role=ChatRole.ASSISTANT, content="在的", created_at=2.0),
                )
            ),
        )

        tail = await self.repos.session.load(key, limit=1)

        self.assertEqual(_contents(tail), ["在的"])

    async def test_append_keeps_previous(self) -> None:
        """再追加一轮不丢旧问答"""
        key = _session_key()
        await self.repos.session.apply_patch(
            key,
            SessionPatchDTO(
                append=(
                    MessageDTO(role=ChatRole.USER, content="你好", created_at=1.0),
                    MessageDTO(role=ChatRole.ASSISTANT, content="在的", created_at=2.0),
                )
            ),
        )

        await self.repos.session.apply_patch(
            key,
            SessionPatchDTO(append=(MessageDTO(role=ChatRole.USER, content="第三条"),)),
        )

        self.assertEqual(
            _contents(await self.repos.session.load(key)), ["你好", "在的", "第三条"]
        )

    async def test_reset_to_system_empties_rows(self) -> None:
        """重置清空消息行"""
        key = _session_key()
        await self.repos.session.apply_patch(
            key,
            SessionPatchDTO(append=(MessageDTO(role=ChatRole.USER, content="你好"),)),
        )

        reset = await self.repos.session.apply_patch(
            key, SessionPatchDTO(reset_to_system=True)
        )

        self.assertEqual(reset.messages, ())

    async def test_delete_one_key_leaves_others(self) -> None:
        """按键清除连带消息行，另一串不动，键不在库内即零"""
        mine = SessionKey(f"{Platform.TELEGRAM}.g100456")
        theirs = SessionKey(f"{Platform.TELEGRAM}.g100789")
        await self._seed(mine, "我的问答")
        await self._seed(theirs, "别人的问答")

        self.assertEqual(await self.repos.session.delete(mine), 1)
        self.assertEqual(await self.repos.session.delete(mine), 0)

        self.assertEqual(_contents(await self.repos.session.load(mine)), [])
        self.assertEqual(
            (await _one(self.conn, "SELECT COUNT(*) FROM session WHERE key = ?", mine))[
                0
            ],
            0,
        )
        self.assertEqual(
            _contents(await self.repos.session.load(theirs)), ["别人的问答"]
        )

    async def test_delete_all_empties_both_tables(self) -> None:
        """整表清除跨会话生效"""
        other = SessionKey(f"{Platform.TELEGRAM}.g100456")
        await self._seed(_session_key(), "本串问答")
        await self._seed(other, "另一群")

        await self.repos.session.delete_all()

        self.assertEqual(_contents(await self.repos.session.load(other)), [])
        self.assertEqual((await _one(self.conn, "SELECT COUNT(*) FROM session"))[0], 0)
        self.assertEqual(
            (await _one(self.conn, "SELECT COUNT(*) FROM session_message"))[0], 0
        )

    async def test_delete_idle_clears_stale_and_empty(self) -> None:
        """按最后问答时间清闲置，没消息的会话按零计一并清"""
        live = SessionKey(f"{Platform.TELEGRAM}.g100456")
        stale = SessionKey(f"{Platform.TELEGRAM}.g100789")
        empty = SessionKey(f"{Platform.TELEGRAM}.g100999")
        await self._seed(live, "新问答", created_at=_LIVE_AT)
        await self._seed(stale, "旧问答", created_at=_STALE_AT)
        await self.repos.session.apply_patch(
            empty, SessionPatchDTO(reset_to_system=True)
        )

        self.assertEqual(await self.repos.session.delete_idle(_DEADLINE), 2)

        self.assertEqual(_contents(await self.repos.session.load(stale)), [])
        self.assertEqual(_contents(await self.repos.session.load(live)), ["新问答"])
        self.assertEqual((await _one(self.conn, "SELECT COUNT(*) FROM session"))[0], 1)
        self.assertEqual(
            (await _one(self.conn, "SELECT COUNT(*) FROM session_message"))[0], 1
        )

    async def _seed(
        self, key: SessionKey, content: str, *, created_at: float = 1.0
    ) -> None:
        """往库里塞一条问答"""
        await self.repos.session.apply_patch(
            key,
            SessionPatchDTO(
                append=(
                    MessageDTO(
                        role=ChatRole.USER, content=content, created_at=created_at
                    ),
                )
            ),
        )


class TestTask(_RealDb):
    """任务去重、状态机与清死行"""

    async def asyncSetUp(self) -> None:
        # task 外键指向 principal，先落一行主体，否则入队当场拒
        await super().asyncSetUp()
        await self.repos.principal.upsert(_principal(), "张三")

    async def test_dedupe_returns_existing(self) -> None:
        """同一去重键命中未完成任务即回原任务"""
        request = self._request(dedupe_key="k-1", payload=_CHAT_PAYLOAD)

        first = await self.repos.task.insert(request)
        again = await self.repos.task.insert(request)

        self.assertEqual(first.task_id, again.task_id)
        self.assertEqual(first.status, TaskStatus.PENDING)

    async def test_empty_dedupe_never_collides(self) -> None:
        """空去重键不得互相挡住"""
        hist = await self.repos.task.insert(
            self._request(kind=TaskKind.HISTORY, priority=TaskPriority.HIGH)
        )
        clear = await self.repos.task.insert(
            self._request(kind=TaskKind.CLEAR, priority=TaskPriority.IMMEDIATE)
        )

        self.assertNotEqual(hist.task_id, clear.task_id)

    async def test_patch_records_started_at(self) -> None:
        """转执行中写回开始时刻，载荷与主体原样读回"""
        first = await self.repos.task.insert(
            self._request(dedupe_key="k-1", payload=_CHAT_PAYLOAD)
        )

        running = await self.repos.task.patch(
            first.task_id, TaskPatchDTO(status=TaskStatus.RUNNING)
        )

        assert running is not None
        self.assertEqual(running.status, TaskStatus.RUNNING)
        self.assertIsNotNone(running.started_at)
        self.assertEqual(running.payload, _CHAT_PAYLOAD)
        self.assertEqual(running.source_ref, _ref())
        self.assertEqual(running.principal, _principal())

    async def test_illegal_transition_is_refused(self) -> None:
        """执行中不得退回排队，库内状态不动"""
        first = await self.repos.task.insert(self._request(dedupe_key="k-1"))
        await self.repos.task.patch(
            first.task_id, TaskPatchDTO(status=TaskStatus.RUNNING)
        )

        self.assertIsNone(
            await self.repos.task.patch(
                first.task_id, TaskPatchDTO(status=TaskStatus.PENDING)
            )
        )
        current = await self.repos.task.find(first.task_id)
        assert current is not None
        self.assertEqual(current.status, TaskStatus.RUNNING)

    async def test_final_state_has_no_exit(self) -> None:
        """终态写错误串与结束时刻，且不得复活"""
        first = await self.repos.task.insert(self._request(dedupe_key="k-1"))
        await self.repos.task.patch(
            first.task_id, TaskPatchDTO(status=TaskStatus.RUNNING)
        )

        failed = await self.repos.task.patch(
            first.task_id, TaskPatchDTO(status=TaskStatus.FAILED, error_text="炸了")
        )

        assert failed is not None
        self.assertIsNotNone(failed.finished_at)
        self.assertEqual(failed.error_text, "炸了")
        self.assertIsNone(
            await self.repos.task.patch(
                first.task_id, TaskPatchDTO(status=TaskStatus.RUNNING)
            )
        )

    async def test_patch_missing_row_returns_none(self) -> None:
        """改不存在的任务返回空"""
        self.assertIsNone(
            await self.repos.task.patch(
                TaskId("不存在.id"), TaskPatchDTO(status=TaskStatus.RUNNING)
            )
        )

    async def test_list_unfinished_orders_by_priority(self) -> None:
        """未完成任务按优先级升序、同档按入队序"""
        principal = _principal()
        await self.repos.principal.upsert(principal, "张三")
        await self.repos.task.insert(self._request())
        await self.repos.task.insert(
            self._request(kind=TaskKind.HISTORY, priority=TaskPriority.HIGH)
        )
        await self.repos.task.insert(
            self._request(kind=TaskKind.CLEAR, priority=TaskPriority.IMMEDIATE)
        )

        unfinished = await self.repos.task.list_unfinished(principal.key)

        self.assertEqual(
            [task.kind for task in unfinished],
            [TaskKind.CLEAR, TaskKind.HISTORY, TaskKind.CHAT],
        )

    async def test_startup_marks_every_open_task_dead(self) -> None:
        """启动清死行把排队中与执行中一并判死"""
        chat = await self.repos.task.insert(self._request(dedupe_key="k-1"))
        await self.repos.task.insert(self._request(kind=TaskKind.CLEAR))
        await self.repos.task.patch(
            chat.task_id, TaskPatchDTO(status=TaskStatus.RUNNING)
        )

        self.assertEqual(await purge_dead_tasks(self.conn), 2)

        self.assertEqual(await self.repos.task.list_unfinished(chat.principal.key), ())
        row = await _one(
            self.conn, "SELECT status, finished_at FROM task WHERE id = ?", chat.task_id
        )
        self.assertEqual(row["status"], TaskStatus.FAILED)
        self.assertIsNotNone(row["finished_at"])

    async def test_delete_by_principal(self) -> None:
        """按主体清除名下全部任务"""
        principal = _principal()
        await self.repos.principal.upsert(principal, "张三")
        await self.repos.task.insert(self._request(dedupe_key="k-1"))
        await self.repos.task.insert(self._request(kind=TaskKind.CLEAR))

        self.assertEqual(await self.repos.task.delete_by_principal(principal.key), 2)

    def _request(
        self,
        *,
        kind: TaskKind = TaskKind.CHAT,
        priority: TaskPriority = TaskPriority.NORMAL,
        dedupe_key: str = "",
        payload: TaskPayload = (),
    ) -> TaskRequestDTO:
        """构造一条入队请求"""
        return TaskRequestDTO(
            principal=_principal(),
            kind=kind,
            source_ref=_ref(),
            priority=priority,
            dedupe_key=dedupe_key,
            payload=payload,
        )


class TestGrant(_RealDb):
    """授权档位增删与到期判定"""

    async def test_grant_revoke_once(self) -> None:
        """新增为真、重复为假、撤销同理"""
        principal = _principal()
        user = UserId("456")

        self.assertTrue(await self.repos.grant.grant(user, principal.key))
        self.assertTrue(await self.repos.grant.contains(user))
        self.assertFalse(await self.repos.grant.grant(user, principal.key))
        self.assertTrue(await self.repos.grant.revoke(user))
        self.assertFalse(await self.repos.grant.contains(user))
        self.assertFalse(await self.repos.grant.revoke(user))

    async def test_expired_grant_misses(self) -> None:
        """过期授权不命中，未过期命中"""
        principal = _principal()
        expired = UserId("777")
        live = UserId("888")

        self.assertTrue(
            await self.repos.grant.grant(expired, principal.key, expires_at=1.0)
        )
        self.assertFalse(await self.repos.grant.contains(expired))
        self.assertTrue(
            await self.repos.grant.grant(live, principal.key, expires_at=9e18)
        )
        self.assertTrue(await self.repos.grant.contains(live))

    async def test_list_active_skips_expired_and_revoked(self) -> None:
        """未到期的按授权先后列出，过期与已撤销的不出现"""
        principal = _principal()
        forever = UserId("111")
        timed = UserId("222")
        await self.repos.grant.grant(forever, principal.key)
        await self.repos.grant.grant(timed, principal.key, expires_at=9e18)
        await self.repos.grant.grant(UserId("333"), principal.key, expires_at=1.0)
        dropped = UserId("444")
        await self.repos.grant.grant(dropped, principal.key)
        await self.repos.grant.revoke(dropped)

        self.assertEqual((forever, timed), await self.repos.grant.list_active())


class TestMedia(_RealDb):
    """媒体索引同键收敛与按容器清除"""

    async def test_register_locates_latest_per_slot(self) -> None:
        """同种类重复登记收敛到一行，不同槽位各留一条"""
        principal = _principal()
        ref = _ref()
        await self._register(ref, ContentKind.PHOTO, "a/b.png")
        await self._register(ref, ContentKind.PHOTO, "a/c.png")

        located = await self.repos.media.locate(ref)
        self.assertEqual(len(located), 1)
        self.assertEqual(located[0].local_path, "a/c.png")

        await self._register(ref, ContentKind.DOCUMENT, "a/d.pdf", slot=1)

        self.assertEqual(
            [entry.slot for entry in await self.repos.media.locate(ref)], [0, 1]
        )
        self.assertEqual(await self.repos.media.delete_by_principal(principal.key), 2)
        self.assertEqual(await self.repos.media.locate(ref), ())

    async def _register(
        self, ref: MsgReferenceDTO, kind: ContentKind, local_path: str, *, slot: int = 0
    ) -> None:
        """登记一条媒体索引"""
        await self.repos.media.register(
            ref, MediaEntryDTO(kind=kind, local_path=local_path, slot=slot)
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
