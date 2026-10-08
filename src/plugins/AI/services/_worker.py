# src/plugins/AI/services/_worker.py
"""对话工作循环

- 实现流式接收、UI 更新与记录持久化
"""

import asyncio
import time
from collections.abc import AsyncGenerator
from typing import Any, Literal

from aiogram.exceptions import TelegramBadRequest

from utils import get_logger

from ...messages import BotMessage
from ..config import ai_config
from ..core import AIClient, AITaskStoppedError, TelegramTaskItem, user_sessions
from ..utils import build_message, make_data
from ._render import render_html, screenshot

logger = get_logger("Plg.AI.Worker")


async def _send_long_message(task: TelegramTaskItem, text: str) -> None:
    """分段发送长消息

    - 内置防频控
    """
    total_len = len(text)
    size = ai_config.msg_chunk_size
    total_chunks = (total_len + size - 1) // size

    for idx, i in enumerate(range(0, total_len, size)):
        chunk = text[i : i + size]
        try:
            await task.safe_reply(chunk)
        except TelegramBadRequest as e:
            logger.send_error("分段消息请求错误", e)
        except Exception as e:
            logger.send_error("分段消息未知错误", e)

        # 如果总段数超过阈值，且当前不是最后一段，则在发送后休眠防频控
        if total_chunks > ai_config.flood_threshold and idx < total_chunks - 1:
            await asyncio.sleep(1)


async def _save_conversation_record(user: str, text: str, final_msg: str) -> None:
    """写入对话记录"""
    rec_dir = ai_config.record_dir

    try:
        # 生成 HTML 并截图
        html_path = ai_config.record_dir / f"temp/{user}.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(render_html(final_msg))
        await screenshot(user, html_path)

        # 格式化并写入 TXT 和 MD
        wrt = (
            f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}\n\n"
            f"用户：{text}\n\n"
            f"AI回复：\n{final_msg}\n\n\n"
        )
        with open(rec_dir / f"staged/{user}.txt", "a", encoding="utf8") as f:
            f.write(wrt)
        with open(rec_dir / f"temp/{user}.md", "a", encoding="utf8") as f:
            f.write(wrt)
    except Exception as e:
        logger.send_error("保存本地对话记录失败", e)


async def _handle_ai_message(
    user: str, text: str
) -> AsyncGenerator[tuple[Literal["final", "error"], Any], None]:
    """处理 AI 流式数据

    - 产出 (事件类型, 数据)
    """
    session = user_sessions[user]
    current_msg = ""
    msg = make_data(session, text)

    try:
        async for delta in AIClient.stream_chat(msg):
            # 处理正文内容
            if (content := delta.get("content")) is not None:
                if content.startswith("\n\n"):
                    content = content[2:]
                current_msg += content
        yield "final", current_msg
    except Exception as e:
        yield "error", e


async def _send_final_reply(task: TelegramTaskItem, final_msg: str) -> None:
    """发送最终回复"""
    if len(final_msg) > ai_config.msg_chunk_size:
        await _send_long_message(task, final_msg)
    else:
        await task.safe_reply(final_msg)


async def worker_loop(task: TelegramTaskItem, user: str) -> None:
    """核心工作循环"""
    message = task.message
    text = message.text
    if text is None:
        logger.debug("消息无文本，跳过")
        return

    session = user_sessions[user]
    final_msg = ""
    has_error = False

    try:
        async for event_type, data in _handle_ai_message(user, text):
            match event_type:
                case "final":
                    final_msg = data
                case "error":
                    logger.send_error("流式处理错误", data)
                    has_error = True

        if has_error or not final_msg:
            await task.safe_reply(BotMessage.AI_UNAVAILABLE)
            return

        await _send_final_reply(task, final_msg)

        session.message.extend(
            [build_message("user", text), build_message("assistant", final_msg)]
        )

        await _save_conversation_record(user, text, final_msg)

    except AITaskStoppedError:
        raise
    except Exception as e:
        logger.send_error("Worker 运行时错误", e)
        await task.safe_reply(BotMessage.AI_UNAVAILABLE)
