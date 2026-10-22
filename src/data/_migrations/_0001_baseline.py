# src/data/_migrations/_0001_baseline.py
"""基线建表

- 建立主体、会话、会话消息、群流水、任务、媒体、授权与版本表
- 全部语句在同一事务内执行
"""

import aiosqlite

from core.domain import TaskStatus

_TABLES: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS principal(
        key            TEXT PRIMARY KEY,
        platform       TEXT NOT NULL,
        container      TEXT NOT NULL,
        user           TEXT NOT NULL,
        display_name   TEXT NOT NULL DEFAULT '',
        created_at     REAL NOT NULL,
        last_active_at REAL NOT NULL DEFAULT 0,
        is_active      INTEGER NOT NULL DEFAULT 0
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_principal_platform ON principal(platform)",
    "CREATE INDEX IF NOT EXISTS idx_principal_stale ON principal(last_active_at, is_active)",
    """
    CREATE TABLE IF NOT EXISTS session(
        key            TEXT PRIMARY KEY,
        container_name TEXT NOT NULL DEFAULT '',
        summary        TEXT NOT NULL DEFAULT '',
        last_active_at REAL NOT NULL DEFAULT 0,
        is_active      INTEGER NOT NULL DEFAULT 0
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS session_message(
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        session_key TEXT NOT NULL REFERENCES session(key) ON DELETE CASCADE,
        seq         INTEGER NOT NULL,
        role        TEXT NOT NULL,
        sender_id   TEXT NOT NULL DEFAULT '',
        sender_name TEXT NOT NULL DEFAULT '',
        content     TEXT NOT NULL,
        created_at  REAL NOT NULL
    )
    """,
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_message_seq ON session_message(session_key, seq)",
    """
    CREATE TABLE IF NOT EXISTS group_message(
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        session_key TEXT NOT NULL REFERENCES session(key) ON DELETE CASCADE,
        message_id  TEXT NOT NULL,
        sender_id   TEXT NOT NULL,
        sender_name TEXT NOT NULL DEFAULT '',
        content     TEXT NOT NULL,
        created_at  REAL NOT NULL
    )
    """,
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_groupmsg_msg ON group_message(session_key, message_id)",
    "CREATE INDEX IF NOT EXISTS idx_groupmsg_time ON group_message(session_key, created_at)",
    """
    CREATE TABLE IF NOT EXISTS task(
        id         TEXT PRIMARY KEY,
        principal  TEXT NOT NULL REFERENCES principal(key) ON DELETE CASCADE,
        kind       TEXT NOT NULL,
        priority   INTEGER NOT NULL,
        sequence   INTEGER NOT NULL,
        status     TEXT NOT NULL,
        payload    TEXT NOT NULL DEFAULT '[]',
        source_ref TEXT NOT NULL,
        dedupe_key TEXT NOT NULL DEFAULT '',
        error      TEXT NOT NULL DEFAULT '',
        created_at REAL NOT NULL,
        started_at REAL,
        finished_at REAL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_task_pending ON task(principal, status, priority, sequence)",
    "CREATE INDEX IF NOT EXISTS idx_task_unfinish ON task(status)",
    (
        # 去重键为空串表示不查重，空串互不相同才不挡并发对话
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_task_dedupe ON task(dedupe_key) "
        f"WHERE status IN ('{TaskStatus.PENDING}', '{TaskStatus.RUNNING}') "
        "AND dedupe_key <> ''"
    ),
    """
    CREATE TABLE IF NOT EXISTS media_asset(
        platform   TEXT NOT NULL,
        container  TEXT NOT NULL,
        message_id TEXT NOT NULL,
        kind       TEXT NOT NULL,
        slot       INTEGER NOT NULL DEFAULT 0,
        local_path TEXT NOT NULL,
        size_bytes INTEGER NOT NULL DEFAULT 0,
        meta       TEXT NOT NULL DEFAULT '{}',
        created_at REAL NOT NULL,
        PRIMARY KEY (platform, container, message_id, kind, slot)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_media_container ON media_asset(platform, container)",
    """
    CREATE TABLE IF NOT EXISTS grant(
        user_key   TEXT PRIMARY KEY,
        granted_by TEXT NOT NULL,
        expires_at REAL,
        created_at REAL NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS schema_version(
        version    INTEGER PRIMARY KEY,
        applied_at REAL NOT NULL,
        checksum   TEXT NOT NULL
    )
    """,
)


async def apply(conn: aiosqlite.Connection) -> None:
    """执行基线建表与建索引"""
    for ddl in _TABLES:
        await conn.execute(ddl)
