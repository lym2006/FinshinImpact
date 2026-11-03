# src/plugins/AI/services/_cleanup.py
"""会话清理服务

- 过期记录与闲置会话按保留期后台清理
- 清理轮间隔改了当轮即按新值重排
"""

import asyncio
import contextlib
import time
from typing import NoReturn

from core.domain.ids import SessionKey
from services.tasks import get_task_service
from utils import get_logger

from ..config import ai_config
from ..core import (
    active_tasks,
    purge_idle_sessions,
    purge_pending,
    purge_sessions,
)

_logger = get_logger("Plg.AI.Cleanup")

# 配置生效那一叫的旗，醒了就按新间隔重排
_wakeup = asyncio.Event()


async def _sleep_or_wake(seconds: float) -> None:
    """睡到点，或被配置生效提前叫醒"""
    _wakeup.clear()
    with contextlib.suppress(TimeoutError):
        await asyncio.wait_for(_wakeup.wait(), timeout=seconds)


async def wake_cleanup(*_args: object) -> None:
    """叫醒清理循环，配置生效时机被召唤"""
    _wakeup.set()


def _purge_records(deadline: float) -> tuple[SessionKey, ...]:
    """清除过期落盘记录

    - 一群一份、一私聊一份，文件时间即最后一次问答时间
    - 交出被清文件的会话键，同键上下文交调用者一并作废
    """
    expired: list[SessionKey] = []
    for path in ai_config.record_dir.glob("*.md"):
        try:
            if path.stat().st_mtime < deadline:
                path.unlink(missing_ok=True)
                _logger.info(f"清理过期记录: {path.name}")
                expired.append(SessionKey(path.stem))
        except OSError as e:
            _logger.send_error(f"清理记录文件失败: {path.name}", e)
    return tuple(expired)


async def _release_inflight() -> None:
    """收掉在途问答与压缩协程"""
    await get_task_service().release()

    # 摘要压缩不排队，停服时单独收
    tasks = list(active_tasks)
    active_tasks.clear()
    for task in tasks:
        task.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


async def cleanup_loop() -> NoReturn:
    """后台清理闲置记录

    - 记录按文件时间清，库内上下文按最后问答时间清
    - 起手先按记号补完上次断掉的历史清理
    """
    try:
        await purge_pending()
        while True:
            deadline = time.time() - ai_config.keep_seconds

            purged = await purge_sessions(_purge_records(deadline))
            purged += await purge_idle_sessions(deadline)
            if purged:
                _logger.info(f"清理过期上下文: {purged} 串")

            # 扫完再睡，启动即扫一遍重启前攒下的记录
            await _sleep_or_wake(ai_config.waiting_time)
    finally:
        await _release_inflight()
