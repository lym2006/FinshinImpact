# src/plugins/AI/core/_store.py
"""会话落库

- 按会话键读写消息，仓储首次用时装配
"""

import asyncio
from collections import defaultdict

from core.contracts import SessionRepository
from core.domain.ids import SessionKey
from core.dto import MessageDTO, SessionDTO, SessionPatchDTO
from data import build_repositories, get_connection
from utils.paths import DB_FILE

# 同会话两路并发写会算出同一个序号，写入按会话键串行
_write_locks: dict[SessionKey, asyncio.Lock] = defaultdict(asyncio.Lock)
_session_repo: SessionRepository | None = None


async def _repo() -> SessionRepository:
    """取出会话仓储

    - 首次调用装配，之后每次走同一条连接
    """
    global _session_repo
    if _session_repo is None:
        conn = await get_connection(DB_FILE)
        _session_repo = build_repositories(conn).session
    return _session_repo


async def read_session(session_key: SessionKey) -> SessionDTO:
    """读会话快照

    - 库里没建过这串会话即返回空快照
    """
    return await (await _repo()).load(session_key)


async def save_session(session_key: SessionKey, window: tuple[MessageDTO, ...]) -> None:
    """覆盖写会话窗口

    - 人设首行随窗口一起重作，序号从头排
    """
    async with _write_locks[session_key]:
        repo = await _repo()
        await repo.apply_patch(
            session_key, SessionPatchDTO(append=window, reset_to_system=True)
        )


async def clear_session(session_key: SessionKey) -> None:
    """清空会话消息

    - 人设首行随后一轮重建
    """
    async with _write_locks[session_key]:
        repo = await _repo()
        await repo.apply_patch(session_key, SessionPatchDTO(reset_to_system=True))
