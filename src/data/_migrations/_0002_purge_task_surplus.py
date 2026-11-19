"""抹掉任务与主体表的废弃列

- 先撤建在这些列上的索引
- 重建按剩余列的任务索引
- 逐列核过在不在再删
"""

import aiosqlite

# 待删的表与列
_DEAD_COLUMNS: tuple[tuple[str, str], ...] = (
    ("task", "priority"),
    ("task", "dedupe_key"),
    ("task", "created_at"),
    ("task", "started_at"),
    ("task", "finished_at"),
    ("task", "error"),
    ("principal", "last_active_at"),
    ("principal", "is_active"),
)

_DROPPED_INDEXES: tuple[str, ...] = (
    "idx_task_pending",
    "idx_task_dedupe",
    "idx_principal_stale",
)

# 删完之后按主体、状态与入队序重建任务索引
_TASK_INDEX = (
    "CREATE INDEX IF NOT EXISTS idx_task_pending ON task(principal, status, sequence)"
)


async def apply(conn: aiosqlite.Connection) -> None:
    """执行任务与主体表废弃列清理"""
    for name in _DROPPED_INDEXES:
        await conn.execute(f"DROP INDEX IF EXISTS {name}")

    for table, column in _DEAD_COLUMNS:
        if await _has_column(conn, table, column):
            await conn.execute(f"ALTER TABLE {table} DROP COLUMN {column}")

    await conn.execute(_TASK_INDEX)


async def _has_column(conn: aiosqlite.Connection, table: str, column: str) -> bool:
    """判断表里有没有这一列"""
    async with conn.execute(f"PRAGMA table_info({table})") as cursor:
        rows = await cursor.fetchall()
    return any(row["name"] == column for row in rows)
