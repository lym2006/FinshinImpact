# src/data/_sqlite/_media.py
"""媒体索引仓储实装

- 按消息定位三元组读写 media_asset 表
"""

import time

import aiosqlite

from core.contracts import MediaRepository
from core.domain import ContentKind, Platform
from core.domain.ids import KEY_SEP, ContainerKey, PrincipalKey
from core.dto import MediaEntryDTO, MsgReferenceDTO


class SqliteMediaRepository(MediaRepository):
    """媒体索引仓储的 SQLite 实装"""

    def __init__(self, conn: aiosqlite.Connection) -> None:
        self._conn = conn

    async def register(self, ref: MsgReferenceDTO, entry: MediaEntryDTO) -> None:
        """登记一条媒体索引

        - 同定位同序号重写即覆盖本地路径与体积
        """
        await self._conn.execute(
            "INSERT INTO media_asset(platform, container, message_id, kind, slot,"
            " local_path, size_bytes, created_at)"
            " VALUES(?, ?, ?, ?, ?, ?, ?, ?)"
            " ON CONFLICT(platform, container, message_id, kind, slot) DO UPDATE SET"
            " local_path = excluded.local_path,"
            " size_bytes = excluded.size_bytes,"
            " created_at = excluded.created_at",
            (
                ref.platform,
                ref.container,
                ref.message_id,
                entry.kind,
                entry.slot,
                entry.local_path,
                entry.size_bytes,
                time.time(),
            ),
        )
        await self._conn.commit()

    async def locate(self, ref: MsgReferenceDTO) -> tuple[MediaEntryDTO, ...]:
        """按三元组定位媒体

        - 同消息多附件按槽位升序
        """
        async with self._conn.execute(
            "SELECT kind, local_path, slot, size_bytes FROM media_asset "
            "WHERE platform = ? AND container = ? AND message_id = ? ORDER BY slot",
            (ref.platform, ref.container, ref.message_id),
        ) as cursor:
            rows = await cursor.fetchall()
        return tuple(
            MediaEntryDTO(
                kind=ContentKind(row["kind"]),
                local_path=row["local_path"],
                slot=row["slot"],
                size_bytes=row["size_bytes"],
            )
            for row in rows
        )

    async def delete_by_principal(self, key: PrincipalKey) -> int:
        """清除主体全部媒体索引

        - 群媒体的索引归容器，群内任一成员清除即整容器生效
        """
        platform, container = _split_container_segment(key)
        async with self._conn.execute(
            "DELETE FROM media_asset WHERE platform = ? AND container = ?",
            (platform, container),
        ) as cursor:
            removed = cursor.rowcount
        await self._conn.commit()
        return removed


def _split_container_segment(key: PrincipalKey) -> tuple[Platform, ContainerKey]:
    """取主体键的平台与容器段"""
    platform, container, _ = key.split(KEY_SEP, 2)
    return Platform(platform), ContainerKey(container)
