# devtools/verify_data_layer.py
r"""data 层验证脚本

- 对临时库跑建表、往返、状态机、去重、清死行、备份与版本保护
- 每项打印一行结果，任一不符即非零退出
- 用法 `python devtools/verify_data_layer.py`
"""

import asyncio
import shutil
import sys
import tempfile
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import aiosqlite  # noqa: E402

from core.domain import (  # noqa: E402
    ChatRole,
    ContentKind,
    Platform,
    TaskKind,
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
    UserKey,
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
    Repositories,
    build_repositories,
    check_schema_compatible,
    get_connection,
    purge_dead_tasks,
    run_migrations,
)

_TMP = Path(tempfile.mkdtemp(prefix="verify-data-"))

# 闲置判定样本时刻（秒），只用于比对清除界限
_STALE_AT = 1.0
_LIVE_AT = 9.0
_DEADLINE = 5.0

# 打开过的库路径，收尾统一关闭连接
_PATHS: list[Path] = []


def _db(name: str) -> tuple[Path, Path]:
    """取一组隔离的临时库路径"""
    root = _TMP / name
    backup = root / "backups"
    root.mkdir(parents=True, exist_ok=True)
    backup.mkdir(parents=True, exist_ok=True)
    db = root / "bot.db"
    _PATHS.append(db)
    return db, backup


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


async def _migrate(db: Path, backup: Path) -> aiosqlite.Connection:
    """建好库结构并交回连接"""
    conn = await get_connection(db)
    await run_migrations(conn, db, backup)
    return conn


async def _one(conn: aiosqlite.Connection, sql: str, *params: str) -> aiosqlite.Row:
    """取单行查询结果

    - 空结果当场断言失败，免得空行渗进后续比对
    """
    async with conn.execute(sql, params) as cursor:
        row = await cursor.fetchone()
    assert row is not None, sql
    return row


async def check_baseline() -> None:
    """建表、版本行与连接参数"""
    db, backup = _db("baseline")
    conn = await _migrate(db, backup)

    async with conn.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table','index')"
    ) as cursor:
        names = {row["name"] for row in await cursor.fetchall()}
    async with conn.execute("SELECT version, checksum FROM schema_version") as cursor:
        rows = list(await cursor.fetchall())
    mode = await _one(conn, "PRAGMA journal_mode")
    foreign_keys = await _one(conn, "PRAGMA foreign_keys")

    expected = {
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
    assert expected <= names, f"缺表或索引：{expected - names}"
    assert [row["version"] for row in rows] == [1], rows
    assert rows[0]["checksum"], "校验和为空"
    assert mode[0] == "wal", mode
    assert foreign_keys[0] == 1, foreign_keys
    print("✅ 建表齐全、版本落一行、WAL 与外键已开")


async def check_roundtrip() -> None:
    """主体与会话读写往返"""
    db, backup = _db("roundtrip")
    conn = await _migrate(db, backup)
    repos = build_repositories(conn)
    principal = _principal()
    key = _session_key()

    saved = await repos.principal.upsert(principal, "张三")
    assert saved == principal
    assert await repos.principal.find_by_key(principal.key) == principal
    assert await repos.principal.find_by_key(PrincipalKey("tg.g1.9")) is None

    await repos.principal.upsert(principal, "李四")
    display = await _one(
        conn, "SELECT display_name FROM principal WHERE key = ?", principal.key
    )
    assert display[0] == "李四"

    assert await repos.session.load(key) == _empty_session(), "缺行应返回空快照"

    patched = await repos.session.apply_patch(
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
                MessageDTO(
                    role=ChatRole.ASSISTANT,
                    content="在的",
                    created_at=2.0,
                ),
            ),
            summary="摘要一",
        ),
    )
    assert [m.content for m in patched.messages] == ["你好", "在的"], patched
    assert patched.messages[0].sender_id == "456"
    assert patched.messages[0].sender_name == "张三"
    assert patched.summary == "摘要一"

    tail = await repos.session.load(key, limit=1)
    assert [m.content for m in tail.messages] == ["在的"], tail

    await repos.session.apply_patch(
        key,
        SessionPatchDTO(append=(MessageDTO(role=ChatRole.USER, content="第三条"),)),
    )
    kept = await repos.session.load(key)
    assert [m.content for m in kept.messages] == ["你好", "在的", "第三条"], kept

    reset = await repos.session.apply_patch(key, SessionPatchDTO(reset_to_system=True))
    assert reset.messages == (), reset

    await _check_delete_all(repos, conn)
    await _check_delete_idle(repos, conn)
    print("✅ 主体往返、会话追加/限量/重置/整表清除/闲置清除")


async def _check_delete_idle(repos: Repositories, conn: aiosqlite.Connection) -> None:
    """按最后问答时间清除闲置会话

    - 问答早于界限的清，没消息的会话按零计一并清
    """
    live = SessionKey(f"{Platform.TELEGRAM}.g100456")
    stale = SessionKey(f"{Platform.TELEGRAM}.g100789")
    empty = SessionKey(f"{Platform.TELEGRAM}.g100999")
    await repos.session.apply_patch(
        live,
        SessionPatchDTO(
            append=(
                MessageDTO(role=ChatRole.USER, content="新问答", created_at=_LIVE_AT),
            )
        ),
    )
    await repos.session.apply_patch(
        stale,
        SessionPatchDTO(
            append=(
                MessageDTO(role=ChatRole.USER, content="旧问答", created_at=_STALE_AT),
            )
        ),
    )
    await repos.session.apply_patch(empty, SessionPatchDTO(reset_to_system=True))

    assert await repos.session.delete_idle(_DEADLINE) == 2
    assert (await repos.session.load(stale)).messages == (), stale
    kept = await repos.session.load(live)
    assert [m.content for m in kept.messages] == ["新问答"], kept
    assert (await _one(conn, "SELECT COUNT(*) FROM session"))[0] == 1
    assert (await _one(conn, "SELECT COUNT(*) FROM session_message"))[0] == 1


async def _check_delete_all(repos: Repositories, conn: aiosqlite.Connection) -> None:
    """整表清除跨会话生效

    - 另一个群另起一串键，清除后两表都得空
    """
    other = SessionKey(f"{Platform.TELEGRAM}.g100456")
    await repos.session.apply_patch(
        other,
        SessionPatchDTO(append=(MessageDTO(role=ChatRole.USER, content="另一群"),)),
    )
    await repos.session.delete_all()
    assert (await repos.session.load(other)).messages == (), other
    assert (await _one(conn, "SELECT COUNT(*) FROM session"))[0] == 0
    assert (await _one(conn, "SELECT COUNT(*) FROM session_message"))[0] == 0


def _empty_session() -> SessionDTO:
    """构造空会话快照供比对"""
    return SessionDTO(platform=Platform.TELEGRAM, container=ContainerKey("g100123"))


async def check_task_rules() -> None:
    """任务去重、状态机与清死行"""
    db, backup = _db("task")
    conn = await _migrate(db, backup)
    repos = build_repositories(conn)
    principal = _principal()
    await repos.principal.upsert(principal, "张三")

    request = TaskRequestDTO(
        principal=principal,
        kind=TaskKind.CHAT,
        source_ref=_ref(),
        priority=TaskPriority.NORMAL,
        dedupe_key="k-1",
        payload=((ChatRole.USER, "同一句话"),),
    )
    first = await repos.task.insert(request)
    again = await repos.task.insert(request)
    assert first.task_id == again.task_id, (first.task_id, again.task_id)
    assert first.status is TaskStatus.PENDING

    hist = await repos.task.insert(
        TaskRequestDTO(
            principal=principal,
            kind=TaskKind.HISTORY,
            source_ref=_ref(),
            priority=TaskPriority.HIGH,
        )
    )
    clear = await repos.task.insert(
        TaskRequestDTO(
            principal=principal,
            kind=TaskKind.CLEAR,
            source_ref=_ref(),
            priority=TaskPriority.IMMEDIATE,
        )
    )
    assert hist.task_id != clear.task_id, "空去重键不得互相挡住"

    running = await repos.task.patch(
        first.task_id, TaskPatchDTO(status=TaskStatus.RUNNING)
    )
    assert running is not None and running.status is TaskStatus.RUNNING, running
    assert running.started_at is not None
    assert running.payload == ((ChatRole.USER, "同一句话"),), running.payload
    assert running.source_ref == _ref()
    assert running.principal == principal

    rejected = await repos.task.patch(
        first.task_id, TaskPatchDTO(status=TaskStatus.PENDING)
    )
    assert rejected is None, rejected
    current = await repos.task.find(first.task_id)
    assert current is not None and current.status is TaskStatus.RUNNING, current

    failed = await repos.task.patch(
        first.task_id, TaskPatchDTO(status=TaskStatus.FAILED, error_text="炸了")
    )
    assert failed is not None and failed.finished_at is not None
    assert failed.error_text == "炸了"
    assert (
        await repos.task.patch(first.task_id, TaskPatchDTO(status=TaskStatus.RUNNING))
        is None
    ), "终态不得复活"
    assert (
        await repos.task.patch(
            TaskId("不存在.id"), TaskPatchDTO(status=TaskStatus.RUNNING)
        )
        is None
    )

    unfinished = await repos.task.list_unfinished(principal.key)
    assert [t.kind for t in unfinished] == [TaskKind.CLEAR, TaskKind.HISTORY], (
        unfinished
    )
    print("✅ 去重返回既有、空键不查重、非法迁移与缺行均拒")


async def check_task_purge() -> None:
    """启动清死行与按主体清除任务"""
    db, backup = _db("task-purge")
    conn = await _migrate(db, backup)
    repos = build_repositories(conn)
    principal = _principal()
    await repos.principal.upsert(principal, "张三")

    chat = await repos.task.insert(
        TaskRequestDTO(
            principal=principal,
            kind=TaskKind.CHAT,
            source_ref=_ref(),
            priority=TaskPriority.NORMAL,
        )
    )
    await repos.task.insert(
        TaskRequestDTO(
            principal=principal,
            kind=TaskKind.CLEAR,
            source_ref=_ref(),
            priority=TaskPriority.IMMEDIATE,
        )
    )
    await repos.task.patch(chat.task_id, TaskPatchDTO(status=TaskStatus.RUNNING))

    # 启动清死行把排队中与执行中一并判死，重发同内容才不会命中永不完成的行
    assert await purge_dead_tasks(conn) == 2
    assert await repos.task.list_unfinished(principal.key) == ()
    row = await _one(
        conn, "SELECT status, finished_at FROM task WHERE id = ?", chat.task_id
    )
    assert row["status"] == TaskStatus.FAILED and row["finished_at"] is not None, row

    assert await repos.task.delete_by_principal(principal.key) == 2
    print("✅ 排队中与执行中一并判死、按主体清除全部任务")


async def check_grant_media() -> None:
    """授权与媒体索引"""
    db, backup = _db("grant-media")
    conn = await _migrate(db, backup)
    repos = build_repositories(conn)
    principal = _principal()

    user_key = UserKey(f"{Platform.TELEGRAM}.456")
    assert await repos.grant.grant(user_key, principal.key) is True
    assert await repos.grant.contains(user_key) is True
    assert await repos.grant.grant(user_key, principal.key) is False
    assert await repos.grant.revoke(user_key) is True
    assert await repos.grant.contains(user_key) is False
    assert await repos.grant.revoke(user_key) is False

    expired = UserKey("tg.777")
    live = UserKey("tg.888")
    assert await repos.grant.grant(expired, principal.key, expires_at=1.0) is True
    assert await repos.grant.contains(expired) is False, "过期授权不得命中"
    assert await repos.grant.grant(live, principal.key, expires_at=9e18) is True
    assert await repos.grant.contains(live) is True

    ref = _ref()
    await repos.media.register(
        ref, MediaEntryDTO(kind=ContentKind.PHOTO, local_path="a/b.png")
    )
    await repos.media.register(
        ref, MediaEntryDTO(kind=ContentKind.PHOTO, local_path="a/c.png")
    )
    located = await repos.media.locate(ref)
    assert len(located) == 1 and located[0].local_path == "a/c.png", located

    await repos.media.register(
        ref, MediaEntryDTO(kind=ContentKind.DOCUMENT, local_path="a/d.pdf", slot=1)
    )
    second = await repos.media.locate(ref)
    assert [m.slot for m in second] == [0, 1], second
    assert await repos.media.delete_by_principal(principal.key) == 2
    assert await repos.media.locate(ref) == ()
    print("✅ 授权新增/重复拒/撤销/过期不命中、媒体同键收敛与按容器清除")


async def check_backup_and_version() -> None:
    """备份份数与高版本拒读"""
    db, backup = _db("backup")
    conn = await _migrate(db, backup)

    # 删掉版本行逼迁移重做，重做即备份一次
    for _ in range(4):
        await conn.execute("DELETE FROM schema_version")
        await conn.commit()
        await run_migrations(conn, db, backup)

    files = sorted(backup.glob("bot-*.db"))
    assert len(files) == 3, files

    await conn.execute("UPDATE schema_version SET version = 999")
    await conn.commit()
    assert await check_schema_compatible(conn) is False

    await conn.execute("UPDATE schema_version SET version = 1")
    await conn.commit()
    assert await check_schema_compatible(conn) is True
    print("✅ 备份只留 3 份、高版本拒读、回本版本可读")


def check_fresh_rerun() -> None:
    """删库重跑幂等"""
    db, backup = _db("fresh")

    # 每段各起一个事件循环，等价于重开进程取新连接
    async def count_objects() -> int:
        conn = await _migrate(db, backup)
        row = await _one(conn, "SELECT COUNT(*) AS n FROM sqlite_master")
        async with conn.execute("SELECT version FROM schema_version") as cursor:
            versions = [r["version"] for r in await cursor.fetchall()]
        await conn.close()
        assert versions == [1], versions
        return int(row["n"])

    before = asyncio.run(count_objects())
    for leftover in db.parent.glob("bot.db*"):
        leftover.unlink()
    after = asyncio.run(count_objects())
    assert before == after, (before, after)
    print("✅ 删库重跑对象数一致、版本行仍是一条")


_CHECKS = (
    check_baseline,
    check_roundtrip,
    check_task_rules,
    check_task_purge,
    check_grant_media,
    check_backup_and_version,
)


def main() -> int:
    """逐项跑验并汇总"""

    async def run_checks() -> None:
        try:
            for check in _CHECKS:
                await check()
        finally:
            # 未关的连接会把工作线程留在退出路径上，进程挂住不退
            for path in _PATHS:
                await (await get_connection(path)).close()

    asyncio.run(run_checks())
    check_fresh_rerun()
    return 0


if __name__ == "__main__":
    code = main()
    shutil.rmtree(_TMP, ignore_errors=True)
    raise SystemExit(code)
