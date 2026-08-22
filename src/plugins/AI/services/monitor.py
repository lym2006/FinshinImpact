# src/plugins/AI/services/monitor.py
"""
AI 监控与清理服务

负责：
- 用户任务队列的持续消费与状态更新
- 后台定期清理不活跃用户会话
"""

import asyncio
import logging
import time
from asyncio import CancelledError
from typing import NoReturn

from aiogram.enums import ChatType

from ..core import TaskStoppedError, task_queues, user_sessions
from ..core.config import CLEARUP_TIME, RECORD_DIR, WAITING_TIME
from ..state import user_locks
from .worker import worker_loop

logger = logging.getLogger("Bot.Plugins.AI.Monitor")


# ==================== 1. 用户任务监控循环 ====================
async def monitor_loop(user: str) -> None:
    """监控用户的任务队列

    当有新任务时，自动消费并执行
    当队列为空时，结束循环并清理资源

    Args:
        user: 用户唯一标识
    """
    session = user_sessions[user]
    queue = task_queues[user]

    try:
        while True:
            task = await queue.peek_front()
            if task is None:
                logger.info(f"{user} 队列为空")
                session.is_active = False
                break

            try:
                preview = "🧠 正在思考中"
                if task.type_ in [ChatType.GROUP, ChatType.SUPERGROUP]:
                    preview += "\n群组不推送思考过程，如需要使用 /history 命令查看"

                await task.safe_edit(preview)
                await worker_loop(task, user)

            except TaskStoppedError:
                logger.warning(f"🚨 {user} 原消息被删除")
                try:
                    await task.safe_delete()
                except Exception as e:
                    logger.warning(f"🚨 状态消息删除错误：{e}")

            except CancelledError:
                logger.warning(f"🚨 {user} 任务被取消")
                raise

            except Exception as e:
                logger.error(f"❌ {user} 任务出错：{e}")
                try:
                    await task.safe_edit("❌ 任务异常终止")
                except Exception:
                    pass

            finally:
                # 无论成功失败，都必须将当前任务出队
                await queue.pop_front()

    except CancelledError:
        logger.warning(f"🚨 {user} 监控循环被取消")
        raise

    except Exception as e:
        logger.error(f"❌ {user} 监控循环崩溃：{e}")

    finally:
        session.is_active = False
        user_locks.pop(user, None)
        logger.info(f"🔓 {user} 监控循环结束")


# ==================== 2. 后台清理循环 ====================
async def cleanup_loop() -> NoReturn:
    """后台清理不活跃用户，防止内存无限膨胀"""
    while True:
        # 放在循环开头，确保启动时立即执行一次清理
        await asyncio.sleep(WAITING_TIME)

        now = time.time()
        users_to_remove = []

        # 使用 list() 创建快照，防止在遍历字典时修改字典大小引发 RuntimeError
        for user, session in list(user_sessions.items()):
            if (
                now - session.last_active > CLEARUP_TIME
                and task_queues[user].size == 0
                and not session.is_active
            ):
                users_to_remove.append(user)

        for user in users_to_remove:
            if user in user_sessions:
                user_sessions.pop(user, None)
                task_queues.pop(user, None)
                paths = [
                    RECORD_DIR / f"temp/{user}.html",
                    RECORD_DIR / f"temp/{user}.png",
                    RECORD_DIR / f"temp/{user}.md",
                ]
                for path in paths:
                    path.unlink(missing_ok=True)
                logger.info(f"🧹 自动清理长时间不活跃的用户会话: {user}")
