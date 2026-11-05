# src/bundled/AI/services/_ai_chat.py
"""对话分发服务

- 问答入队与单条消费
"""

from asyncio import CancelledError

from core.domain import TaskHandler, TaskKind
from exceptions import MessageVanishedError
from services.context import HandlerContext
from services.tasks import TaskItem, get_task_service
from utils import get_logger

from ..utils import make_session_key
from .worker import worker_loop

_logger = get_logger("Plg.AI")


async def handle_ai_chat(ctx: HandlerContext) -> None:
    """把一次问答排进本容器的队列"""
    key = make_session_key(ctx.event.principal)
    service = get_task_service()
    await service.enqueue(
        TaskItem(
            container_key=key,
            principal_key=ctx.event.principal.key,
            kind=TaskKind.CHAT,
            ctx=ctx,
        )
    )
    _logger.info(f"容器 {key} 新任务入队，当前长度: {service.size(key)}")


async def _run_chat_task(ctx: HandlerContext) -> None:
    """消费一条问答

    - 原消息被删只记账，取消照线上抛，其余报错交上报
    """
    key = make_session_key(ctx.event.principal)
    try:
        await worker_loop(ctx)
    except MessageVanishedError:
        _logger.error(f"{key} 原消息被删除")
    except CancelledError:
        _logger.error(f"{key} 任务被取消")
        raise
    except Exception as e:
        _logger.send_error(f"{key} 任务出错", e)


chat_task_handler = TaskHandler(kind=TaskKind.CHAT, run=_run_chat_task)
