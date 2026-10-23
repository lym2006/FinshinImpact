# src/plugins/AI/core/_store.py
"""会话落库

- 按会话键读写消息，仓储首次用时装配
- 摘要按会话键覆盖写入
- 人设或主人变更后清掉全部会话与落盘记录
- 闲置够久的会话按最后问答时间清除
"""

import asyncio
from collections import defaultdict

from core.contracts import SessionRepository
from core.domain.ids import SessionKey
from core.dto import MessageDTO, SessionDTO, SessionPatchDTO
from data import build_repositories, get_connection
from utils.paths import DB_FILE

from ..config import ai_config
from ..utils import matches_persona

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


async def save_summary(session_key: SessionKey, summary: str) -> bool:
    """覆盖写会话摘要

    - 新摘要整段顶掉旧的
    - 串里人设行对不上当前正文即视为会话已清，摘要不落
    - 返回是否写入
    """
    async with _write_locks[session_key]:
        repo = await _repo()
        snapshot = await repo.load(session_key)
        if not matches_persona(ai_config.init[0]["content"], snapshot.messages):
            return False
        await repo.apply_patch(session_key, SessionPatchDTO(summary=summary))
        return True


async def clear_session(session_key: SessionKey) -> None:
    """清空会话消息与摘要

    - 人设首行随后一轮重建
    """
    async with _write_locks[session_key]:
        repo = await _repo()
        await repo.apply_patch(
            session_key, SessionPatchDTO(reset_to_system=True, summary="")
        )


async def purge_history() -> None:
    """清空全部会话与落盘记录

    - 换过人设或主人后所有人的历史一并作废
    """
    await (await _repo()).delete_all()
    for path in ai_config.record_dir.glob("*.md"):
        path.unlink(missing_ok=True)


async def purge_sessions(session_keys: tuple[SessionKey, ...]) -> int:
    """按会话键清除上下文

    - 逐键删，键不在库内即零
    - 返回清除条数
    """
    repo = await _repo()
    removed = 0
    for key in session_keys:
        removed += await repo.delete(key)
    return removed


async def purge_idle_sessions(before: float) -> int:
    """清除最后问答时间早于界限的会话

    - 返回清除条数
    """
    return await (await _repo()).delete_idle(before)
