# src/data/_sqlite/_grant.py
"""命令授权仓储实装

- 按用户二段键读写 grant 表
"""

import time

import aiosqlite

from core.contracts import GrantRepository
from core.domain.ids import PrincipalKey, UserKey


class SqliteGrantRepository(GrantRepository):
    """命令授权仓储的 SQLite 实装"""

    def __init__(self, conn: aiosqlite.Connection) -> None:
        self._conn = conn

    async def grant(
        self,
        user_key: UserKey,
        granted_by: PrincipalKey,
        expires_at: float | None = None,
    ) -> bool:
        """授予权限

        - 返回是否新增
        - 已有授权保持原值不改
        """
        async with self._conn.execute(
            "INSERT OR IGNORE INTO grant(user_key, granted_by, expires_at, created_at)"
            " VALUES(?, ?, ?, ?)",
            (user_key, granted_by, expires_at, time.time()),
        ) as cursor:
            added = cursor.rowcount == 1
        await self._conn.commit()
        return added

    async def revoke(self, user_key: UserKey) -> bool:
        """撤销权限

        - 返回是否存在
        """
        async with self._conn.execute(
            "DELETE FROM grant WHERE user_key = ?", (user_key,)
        ) as cursor:
            existed = cursor.rowcount == 1
        await self._conn.commit()
        return existed

    async def contains(self, user_key: UserKey) -> bool:
        """判定是否命中

        - 过期时间已到不算命中
        """
        async with self._conn.execute(
            "SELECT 1 FROM grant WHERE user_key = ?"
            " AND (expires_at IS NULL OR expires_at > ?)",
            (user_key, time.time()),
        ) as cursor:
            return await cursor.fetchone() is not None
