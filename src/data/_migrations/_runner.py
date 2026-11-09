# src/data/_migrations/_runner.py
"""迁移运行器

- 按版本号顺序补做未应用的脚本，库里已经有表才先备份整库
- 校验库结构是否在当前代码可读范围
- 把未跑完的任务判死
"""

import hashlib
import inspect
import shutil
import time
from datetime import datetime
from pathlib import Path
from types import ModuleType

import aiosqlite

from finshin_sdk.domain import TaskStatus

from . import _0001_baseline, _0002_purge_task_surplus, _0003_purge_session_surplus

# 代码内置的结构版本，库内更高即拒绝启动
SUPPORTED_SCHEMA = 3

# 版本号与脚本模块的对照，升序即执行顺序
_MIGRATIONS: tuple[tuple[int, ModuleType], ...] = (
    (1, _0001_baseline),
    (2, _0002_purge_task_surplus),
    (3, _0003_purge_session_surplus),
)

_BACKUP_KEEP = 3  # 超出份数即删最旧

# 含微秒，同一秒内连续迁移才不会互相覆盖
_BACKUP_STAMP = "%Y%m%d-%H%M%S-%f"
_BACKUP_SUFFIX = ".db"
_VERSION_TABLE = "schema_version"


async def run_migrations(
    conn: aiosqlite.Connection, db_path: Path, backup_dir: Path
) -> None:
    """把库结构补到当前代码支持的版本

    - 一支脚本一个事务，落定才记版本号
    - 动手前整库备份一份，空文件没东西可丢即不备份
    """
    current = await _current_version(conn)
    backed_up = not await _has_tables(conn)

    for version, module in _MIGRATIONS:
        if version <= current:
            continue
        if not backed_up:
            await _backup(db_path, backup_dir, conn)
            backed_up = True
        await module.apply(conn)
        await conn.execute(
            "INSERT INTO schema_version(version, applied_at, checksum) VALUES(?, ?, ?)",
            (version, time.time(), _checksum(module)),
        )
        await conn.commit()


async def check_schema_compatible(conn: aiosqlite.Connection) -> bool:
    """判断库结构版本是否不高于代码支持版本"""
    return await _current_version(conn) <= SUPPORTED_SCHEMA


async def purge_dead_tasks(conn: aiosqlite.Connection) -> int:
    """把中断在半途的任务判为失败

    - 返回判死条数
    - 死行不清，每次启动都把它们当欠账重补一遍
    """
    async with conn.execute(
        "UPDATE task SET status = ? WHERE status IN (?, ?)",
        (TaskStatus.FAILED, TaskStatus.PENDING, TaskStatus.RUNNING),
    ) as cursor:
        affected = cursor.rowcount
    await conn.commit()
    return affected


async def _current_version(conn: aiosqlite.Connection) -> int:
    """读出已应用的最高结构版本

    - 版本表不存在按 0 计
    """
    async with conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
        (_VERSION_TABLE,),
    ) as cursor:
        if await cursor.fetchone() is None:
            return 0

    async with conn.execute(f"SELECT MAX(version) FROM {_VERSION_TABLE}") as cursor:
        row = await cursor.fetchone()
    return int(row[0]) if row and row[0] is not None else 0


async def _has_tables(conn: aiosqlite.Connection) -> bool:
    """判断库里是否已经建过表"""
    async with conn.execute(
        "SELECT 1 FROM sqlite_master"
        " WHERE type IN ('table', 'index') AND name NOT LIKE 'sqlite_%' LIMIT 1"
    ) as cursor:
        return await cursor.fetchone() is not None


async def _backup(db_path: Path, backup_dir: Path, conn: aiosqlite.Connection) -> None:
    """迁移前复制整库文件，并删到只剩保留份数"""
    # WAL 中的已提交内容先落回主文件，复制出的库才完整
    # 这行 pragma 会回一行，不取空就锁着结构，随后的删列当场被拒
    async with conn.execute("PRAGMA wal_checkpoint(FULL)") as cursor:
        await cursor.fetchall()

    stamp = datetime.now().strftime(_BACKUP_STAMP)
    target = backup_dir / f"{db_path.stem}-{stamp}{_BACKUP_SUFFIX}"
    try:
        shutil.copy2(db_path, target)
    except OSError as e:
        raise RuntimeError(f"迁移前备份数据库失败：{e}") from e

    pattern = f"{db_path.stem}-*{_BACKUP_SUFFIX}"
    for old in sorted(backup_dir.glob(pattern), reverse=True)[_BACKUP_KEEP:]:
        old.unlink()


def _checksum(module: ModuleType) -> str:
    """取迁移脚本源码哈希"""
    return hashlib.sha256(inspect.getsource(module).encode("utf-8")).hexdigest()
