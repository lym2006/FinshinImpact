import time
import asyncio
import logging
from aiogram.enums import ChatType

from ..config import CLEARUP_TIME,WAITING_TIME
from ..core import user_session,TaskQueue,TaskStopped
from .worker import worker_loop

logger=logging.getLogger("Bot.Plugins.AI.Monitor")

async def monitor_loop(user:str):
    session=user_session[user]
    queue:TaskQueue=session['queue']
    try:
        while True:
            task=await queue.peek_front()
            if not task:
                logger.info(f"{user} 队列为空")
                session['is_active']=False
                break
            try:
                preview="🧠 正在思考中"
                if task.type in [ChatType.GROUP,ChatType.SUPERGROUP]:
                    preview+="\n群组不推送思考过程，如需要使用 /history 命令查看"
                await task.safe_edit(preview)
                await worker_loop(task,user)
            except TaskStopped:
                logger.warning(f"🚨 {user} 原消息被删除")
                try:
                    await task.safe_delete()
                except:
                    logger.warning(f"🚨 状态消息删除错误：{Exception}")
            except Exception as e:
                if isinstance(e,asyncio.CancelledError):
                    logger.warning(f"🚨 {user} 任务被取消")
                else:
                    logger.error(f"❌ {user} 任务出错：{e}")
                try:
                    await task.safe_edit(f"❌ 任务异常终止")
                except:
                    pass
            finally:
                await queue.pop_front()
    except asyncio.CancelledError:
        logger.warning(f"🚨 {user} 监控循环被取消")
        raise
    except:
        logger.error(f"❌ {user} 监控循环崩溃：{Exception}")
    finally:
        session['is_active']=False
        logger.info(f"{user} 监控循环结束")

async def cleanup_loop():
    while True:
        now=time.time()
        users_to_remove=[]
        for user,session in user_session.items():
            if now-session.get('last_active',0)>CLEARUP_TIME \
             and session['queue'].size==0 and not session['is_active']:
                users_to_remove.append(user)
        for user in users_to_remove:
            if user in user_session:
                del user_session[user]
                logger.info(f"🧹 自动清理长时间不活跃的用户会话: {user}")
        await asyncio.sleep(WAITING_TIME)