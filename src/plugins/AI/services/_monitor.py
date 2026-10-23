# src/plugins/AI/services/_monitor.py
"""队列监控服务

- 实现任务消费与会话清理循环
"""

import asyncio
import time
from asyncio import CancelledError
from typing import NoReturn

from exceptions import MessageVanishedError
from utils import get_logger

from ..config import ai_config
from ..core import purge_idle_sessions, task_queues, user_sessions
from ..state import user_locks
from .worker import worker_loop

_logger = get_logger("Plg.AI.Monitor")


async def monitor_loop(user: str) -> None:
    """监控任务队列

    - 有任务即消费，队列空时清理退出
    """
    session = user_sessions[user]
    queue = task_queues[user]

    try:
        while True:
            # 消费循环：peek 队首，空则置非活跃退出
            ctx = await queue.peek_front()
            if ctx is None:
                _logger.debug(f"{user} 队列为空")
                session.is_active = False
                break

            try:
                await worker_loop(ctx)
            except MessageVanishedError:
                _logger.error(f"{user} 原消息被删除")
            except CancelledError:
                _logger.error(f"{user} 任务被取消")
                raise
            except Exception as e:
                _logger.send_error(f"{user} 任务出错", e)
            finally:
                # 无论成功失败，都必须将当前任务出队
                await queue.pop_front()

    except CancelledError:
        _logger.error(f"{user} 监控循环被取消")
        raise
    except Exception as e:
        # 外层兜底：崩溃只记录不外抛，防拖垮宿主
        _logger.send_error(f"{user} 监控循环崩溃", e)
    finally:
        session.is_active = False
        user_locks.pop(user, None)
        _logger.debug(f"{user} 监控循环结束")


def _purge_records() -> None:
    """清除过期落盘记录

    - 一群一份、一私聊一份，文件时间即最后一次问答时间
    - 内存字典重启即空，落盘记录只认文件自己的时间
    """
    deadline = time.time() - ai_config.keep_seconds
    for path in ai_config.record_dir.glob("*.md"):
        try:
            if path.stat().st_mtime < deadline:
                path.unlink(missing_ok=True)
                _logger.info(f"清理过期记录: {path.name}")
        except OSError as e:
            _logger.send_error(f"清理记录文件失败: {path.name}", e)


async def cleanup_loop() -> NoReturn:
    """后台清理闲置记录

    - 内存会话按最后活跃时间清，记录按文件时间清，库内上下文按最后问答时间清
    - 三路各扫各的，重启后留下的记录与上下文照样扫得到
    """
    while True:
        # 放在循环开头，确保启动时立即执行一次清理
        await asyncio.sleep(ai_config.waiting_time)

        deadline = time.time() - ai_config.keep_seconds

        # list() 快照防遍历途中改字典大小，任务非空或正在应答的用户不动
        idle_users = [
            user
            for user, session in list(user_sessions.items())
            if session.last_active < deadline
            and not session.is_active
            and task_queues[user].size == 0
        ]
        for user in idle_users:
            user_sessions.pop(user, None)
            task_queues.pop(user, None)
            _logger.info(f"清理闲置会话: {user}")

        _purge_records()
        purged = await purge_idle_sessions(deadline)
        if purged:
            _logger.info(f"清理闲置上下文: {purged} 串")
