# src/data/_migrations/_0003_purge_session_surplus.py
"""抹掉会话表上没人写值的列

- 逐列先核在不在，重跑迁移不报错
"""

import aiosqlite

# 待删的表与列
_DEAD_COLUMNS: tuple[tuple[str, str], ...] = (
    ("session", "container_name"),
    ("session", "last_active_at"),
    ("session", "is_active"),
)


async def apply(conn: aiosqlite.Connection) -> None:
    """逐列删除会话表的空列"""
    for table, column in _DEAD_COLUMNS:
        if await _has_column(conn, table, column):
            await conn.execute(f"ALTER TABLE {table} DROP COLUMN {column}")


async def _has_column(conn: aiosqlite.Connection, table: str, column: str) -> bool:
    """判断表里有没有这一列"""
    async with conn.execute(f"PRAGMA table_info({table})") as cursor:
        rows = await cursor.fetchall()
    return any(row["name"] == column for row in rows)
