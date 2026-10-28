# src/plugins/AI/core/_store.py
"""会话落库

- 按会话键读写消息，仓储首次用时装配
- 摘要按会话键覆盖写入
- 人设或主人变更后清掉全部会话与落盘记录，动手前落记号、断在半途由下次启动补完
- 闲置够久的会话按最后问答时间清除
"""

import asyncio
from collections import defaultdict
from pathlib import Path

from core.contracts import SessionRepository
from core.domain.ids import SessionKey
from core.dto import MessageDTO, SessionDTO, SessionPatchDTO
from data import build_repositories, get_connection
from utils import get_logger
from utils.paths import DB_FILE

from ..config import ai_config
from ..utils import matches_persona

# 同会话两路并发写会算出同一个序号，写入按会话键串行
_write_locks: dict[SessionKey, asyncio.Lock] = defaultdict(asyncio.Lock)
_session_repo: SessionRepository | None = None

_logger = get_logger("Plg.AI.Store")

# 清理半途断掉的记号，启动扫描按它补完
_PENDING_MARK = ".pending-clear"


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
    - 动手前先落记号，删不净或中途断掉都靠下次启动补完
    """
    _set_pending_mark(True)
    await (await _repo()).delete_all()
    if _purge_records():
        _set_pending_mark(False)


async def purge_pending() -> None:
    """按记号补完上次没做完的历史清理

    - 记号不在即什么都没断，直接返回
    """
    if not _pending_mark().exists():
        return
    _logger.info("上次历史清理未做完，本次补完")
    await purge_history()


def _pending_mark() -> Path:
    """落盘记录目录里的清理记号文件"""
    return ai_config.record_dir / _PENDING_MARK


def _set_pending_mark(pending: bool) -> None:
    """落或撤清理记号

    - 记号自己动不了只记日志，不挡住清理
    """
    mark = _pending_mark()
    try:
        if pending:
            mark.touch()
        else:
            mark.unlink(missing_ok=True)
    except OSError as e:
        _logger.send_error(f"清理记号动不了: {mark.name}", e)


def _purge_records() -> bool:
    """删净落盘记录，交出是否一个不剩

    - 单个删不掉继续删其他的，留下的靠记号在下一次启动重试
    """
    cleared = True
    for path in ai_config.record_dir.glob("*.md"):
        try:
            path.unlink(missing_ok=True)
        except OSError as e:
            cleared = False
            _logger.send_error(f"落盘记录删不掉: {path.name}", e)
    return cleared


async def purge_stale(persona: str, session_key: SessionKey) -> SessionDTO:
    """库里人设版本对不上即清全部历史，交出清理后的快照

    - 换过人设或主人而不重开程序时，读取与问答两条路都在此收口
    """
    snapshot = await read_session(session_key)
    if snapshot.messages and not matches_persona(persona, snapshot.messages):
        await purge_history()
        snapshot = await read_session(session_key)
    return snapshot


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
