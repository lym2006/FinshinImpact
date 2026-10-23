# src/data/_sqlite/_connection.py
"""SQLite 连接管理

- 按事件循环与库文件缓存连接
- 统一开启 WAL 与外键约束
- 退出时合并 WAL 并逐条关闭
"""

import asyncio
from pathlib import Path

import aiosqlite

# 键含库路径，同循环换库文件另开一条，测试用临时库不串
_connections: dict[tuple[asyncio.AbstractEventLoop, Path], aiosqlite.Connection] = {}


async def get_connection(db_path: Path) -> aiosqlite.Connection:
    """取出当前事件循环的库连接

    - 同一循环同一库复用一条，首次打开即设连接级参数
    """
    key = (asyncio.get_running_loop(), db_path)
    cached = _connections.get(key)
    if cached is not None:
        return cached

    conn = await aiosqlite.connect(db_path)
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA journal_mode=WAL")
    await conn.execute("PRAGMA foreign_keys=ON")
    _connections[key] = conn
    return conn


async def close_all() -> None:
    """合并并关闭全部库连接

    - 已提交内容落回主文件后把 -wal 截成 0
    """
    for key, conn in list(_connections.items()):
        _connections.pop(key, None)
        await conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        await conn.close()
