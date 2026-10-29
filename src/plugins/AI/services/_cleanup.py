# src/plugins/AI/services/_cleanup.py
"""会话清理服务

- 实现过期记录与闲置会话的后台清理
"""

import asyncio
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
    session_states,
)

_logger = get_logger("Plg.AI.Cleanup")


def _purge_records(deadline: float) -> tuple[SessionKey, ...]:
    """清除过期落盘记录

    - 一群一份、一私聊一份，文件时间即最后一次问答时间
    - 内存字典重启即空，落盘记录只认文件自己的时间
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
    """作废会话内存态并收掉在途问答"""
    session_states.clear()
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

    - 内存会话按最后活跃时间清，记录按文件时间清，库内上下文按最后问答时间清
    - 记录一到期即连带清掉同键上下文，两边不分叉
    - 重启后留下的记录与上下文照样扫得到
    - 起手先按记号补完上次断掉的历史清理
    - 收到停服取消时先作废内存态，再收在途问答与压缩
    """
    try:
        await purge_pending()
        while True:
            deadline = time.time() - ai_config.keep_seconds
            service = get_task_service()

            # list() 快照防遍历途中改字典大小，队列非空的容器不动
            idle_keys = [
                key
                for key, state in list(session_states.items())
                if state.last_active < deadline and service.size(key) == 0
            ]
            for key in idle_keys:
                session_states.pop(key, None)
                _logger.info(f"清理闲置会话: {key}")

            purged = await purge_sessions(_purge_records(deadline))
            purged += await purge_idle_sessions(deadline)
            if purged:
                _logger.info(f"清理过期上下文: {purged} 串")

            # 扫完再睡，启动即扫一遍重启前攒下的记录
            await asyncio.sleep(ai_config.waiting_time)
    finally:
        await _release_inflight()
