# src/plugins/AI/services/_monitor.py
"""队列监控服务（内部实现）

- 实现任务消费与会话清理循环
"""

import asyncio
import time
from asyncio import CancelledError
from typing import NoReturn

from aiogram.enums import ChatType

from utils import get_logger

from ..config import ai_config
from ..core import AITaskStoppedError, task_queues, user_sessions
from ..state import user_locks
from ._worker import worker_loop

logger = get_logger("Plg.AI.Monitor")

# ==================== 用户任务监控循环 ====================


async def monitor_loop(user: str) -> None:
    """监控任务队列

    有任务即消费，队列空时清理退出。
    """
    session = user_sessions[user]
    queue = task_queues[user]

    try:
        while True:
            task = await queue.peek_front()
            if task is None:
                logger.debug(f"{user} 队列为空")
                session.is_active = False
                break

            try:
                preview = "🧠 正在思考中"
                if task.type_ in [ChatType.GROUP, ChatType.SUPERGROUP]:
                    preview += "\n群组不推送思考过程，如需要使用 /history 命令查看"

                await task.safe_edit(preview)
                await worker_loop(task, user)

            except AITaskStoppedError:
                logger.error(f"{user} 原消息被删除")
                try:
                    await task.safe_delete()
                except Exception as e:
                    logger.send_error("状态消息删除错误", e)

            except CancelledError:
                logger.error(f"{user} 任务被取消")
                raise

            except Exception as e:
                logger.send_error(f"{user} 任务出错", e)
                try:
                    await task.safe_edit("任务异常终止")
                except Exception:
                    pass

            finally:
                # 无论成功失败，都必须将当前任务出队
                await queue.pop_front()

    except CancelledError:
        logger.error(f"{user} 监控循环被取消")
        raise

    except Exception as e:
        logger.send_error(f"{user} 监控循环崩溃", e)

    finally:
        session.is_active = False
        user_locks.pop(user, None)
        logger.debug(f"{user} 监控循环结束")


# ==================== 后台清理循环 ====================


async def cleanup_loop() -> NoReturn:
    """后台清理不活跃用户，防止内存无限膨胀"""
    rec_dir = ai_config.record_dir

    while True:
        # 放在循环开头，确保启动时立即执行一次清理
        await asyncio.sleep(ai_config.waiting_time)

        now = time.time()
        users_to_remove = []

        # 使用 list() 创建快照，防止在遍历字典时修改字典大小引发 RuntimeError
        for user, session in list(user_sessions.items()):
            if (
                now - session.last_active > ai_config.cleanup_time
                and task_queues[user].size == 0
                and not session.is_active
            ):
                users_to_remove.append(user)

        for user in users_to_remove:
            if user in user_sessions:
                user_sessions.pop(user, None)
                task_queues.pop(user, None)
                paths = [
                    rec_dir / f"temp/{user}.html",
                    rec_dir / f"temp/{user}.png",
                    rec_dir / f"temp/{user}.md",
                ]
                for path in paths:
                    path.unlink(missing_ok=True)
                logger.info(f"清理长时间不活跃会话: {user}")
