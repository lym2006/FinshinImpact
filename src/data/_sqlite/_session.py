# src/data/_sqlite/_session.py
"""会话仓储实装

- 按会话键读写 session 与 session_message 两表
"""

import aiosqlite
from typing import cast

from core.contracts import SessionRepository
from core.domain import ChatRole, Platform
from core.domain.ids import KEY_SEP, ContainerKey, SessionKey
from core.dto import MessageDTO, SessionDTO, SessionPatchDTO


class SqliteSessionRepository(SessionRepository):
    """会话仓储的 SQLite 实装"""

    def __init__(self, conn: aiosqlite.Connection) -> None:
        self._conn = conn

    async def load(
        self, session_key: SessionKey, limit: int | None = None
    ) -> SessionDTO:
        """加载会话快照

        - 会话行不存在返回空快照
        - limit 取会话尾部若干条
        """
        platform, container = _split_session_key(session_key)
        async with self._conn.execute(
            "SELECT container_name, summary, last_active_at, is_active "
            "FROM session WHERE key = ?",
            (session_key,),
        ) as cursor:
            row = await cursor.fetchone()

        return SessionDTO(
            platform=platform,
            container=container,
            messages=await self._messages(session_key, limit),
            summary="" if row is None else row["summary"],
            container_name="" if row is None else row["container_name"],
            is_active=bool(row["is_active"]) if row is not None else False,
            last_active=0.0 if row is None else row["last_active_at"],
        )

    async def apply_patch(
        self, session_key: SessionKey, patch: SessionPatchDTO
    ) -> SessionDTO:
        """应用会话增量

        - 重置先清空历史，追加按当前最大序号续排
        """
        await self._ensure_session(session_key)

        if patch.reset_to_system:
            await self._conn.execute(
                "DELETE FROM session_message WHERE session_key = ?", (session_key,)
            )

        if patch.summary is not None:
            await self._conn.execute(
                "UPDATE session SET summary = ? WHERE key = ?",
                (patch.summary, session_key),
            )

        if patch.append:
            seq = await self._next_seq(session_key)
            for message in patch.append:
                await self._conn.execute(
                    "INSERT INTO session_message(session_key, seq, role, sender_id,"
                    " sender_name, content, created_at) VALUES(?, ?, ?, ?, ?, ?, ?)",
                    (
                        session_key,
                        seq,
                        message.role,
                        message.sender_id,
                        message.sender_name,
                        message.content,
                        message.created_at,
                    ),
                )
                seq += 1

        await self._conn.commit()
        return await self.load(session_key)

    async def delete_all(self) -> None:
        """清除全部会话，消息行随外键级联删除"""
        await self._conn.execute("DELETE FROM session")
        await self._conn.commit()

    async def delete_idle(self, before: float) -> int:
        """清除最后问答时间早于界限的会话

        - 没消息的会话按 0 计，一并清掉
        - 消息行随外键级联删除
        - 返回清除条数
        """
        async with self._conn.execute(
            "DELETE FROM session WHERE COALESCE("
            "(SELECT MAX(created_at) FROM session_message "
            "WHERE session_message.session_key = session.key), 0) < ?",
            (before,),
        ) as cursor:
            removed = cursor.rowcount
        await self._conn.commit()
        return removed

    async def _messages(
        self, session_key: SessionKey, limit: int | None
    ) -> tuple[MessageDTO, ...]:
        """按序号升序取会话消息"""
        sql = (
            "SELECT role, content, sender_id, sender_name, created_at "
            "FROM session_message WHERE session_key = ?"
        )
        params: tuple[object, ...] = (session_key,)
        if limit is None:
            sql += " ORDER BY seq"
        else:
            # 先截尾部再倒排，返回顺序仍是升序
            sql += " ORDER BY seq DESC LIMIT ?"
            params = (session_key, limit)

        async with self._conn.execute(sql, params) as cursor:
            rows = list(await cursor.fetchall())

        if limit is not None:
            rows.reverse()
        return tuple(
            MessageDTO(
                role=ChatRole(row["role"]),
                content=row["content"],
                created_at=row["created_at"],
                sender_id=row["sender_id"],
                sender_name=row["sender_name"],
            )
            for row in rows
        )

    async def _ensure_session(self, session_key: SessionKey) -> None:
        """补建缺失的会话行"""
        await self._conn.execute(
            "INSERT OR IGNORE INTO session(key) VALUES(?)", (session_key,)
        )

    async def _next_seq(self, session_key: SessionKey) -> int:
        """取会话内下一个消息序号"""
        async with self._conn.execute(
            "SELECT COALESCE(MAX(seq), 0) + 1 FROM session_message WHERE session_key = ?",
            (session_key,),
        ) as cursor:
            # 聚合查询恒有一行
            row = cast("aiosqlite.Row", await cursor.fetchone())
        return int(row[0])


def _split_session_key(session_key: SessionKey) -> tuple[Platform, ContainerKey]:
    """拆会话键为平台与容器段"""
    platform, _, container = session_key.partition(KEY_SEP)
    return Platform(platform), ContainerKey(container)
