# src/plugins/AI/services/_worker.py
"""对话工作循环（内部实现）

- 实现流式接收、UI 更新与记录持久化
"""

import asyncio
import time
from collections.abc import AsyncGenerator
from typing import Any

from aiogram.enums import ChatType
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter

from utils import get_logger

from ... import messages as msgs
from ..config import ai_config
from ..core import (
    AIClient,
    AITaskStoppedError,
    TelegramTaskItem,
    user_sessions,
)
from ..utils import build_message, make_data
from ._render import render_html, screenshot

logger = get_logger("Plg.AI.Worker")

# ==================== 内部辅助函数 ====================


def _trim(text: str) -> str:
    """裁剪长文本"""
    return text[-len_:] if len(text) > (len_ := ai_config.trim_preview_len) else text


async def _send_long_message(task: TelegramTaskItem, text: str) -> None:
    """分段发送长消息

    内置防频控。
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


async def _save_conversation_record(
    user: str, text: str, final_msg: str, final_think: str
) -> None:
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
            f"AI思考：\n{final_think}\n\n"
            f"AI回复：\n{final_msg}\n\n\n\n\n"
        )
        with open(rec_dir / f"staged/{user}.txt", "a", encoding="utf8") as f:
            f.write(wrt)
        with open(rec_dir / f"temp/{user}.md", "a", encoding="utf8") as f:
            f.write(wrt)
    except Exception as e:
        logger.send_error("保存本地对话记录失败", e)


# ==================== 流式数据处理 ====================


async def _handle_ai_message(
    user: str, text: str
) -> AsyncGenerator[tuple[str, Any], None]:
    """处理 AI 流式数据

    产出 (事件类型, 数据)。
    """
    session = user_sessions[user]
    current_think = current_msg = ""
    msg = make_data(session, text)

    try:
        async for delta in AIClient.stream_chat(msg):
            # 处理思考过程
            if (reasoning := delta.get("reasoning_content")) is not None:
                if reasoning.endswith("\n"):
                    reasoning = reasoning[:-1]
                current_think += reasoning
                yield "think", current_think

            # 处理正文内容
            if (content := delta.get("content")) is not None:
                if content.startswith("\n\n"):
                    content = content[2:]
                current_msg += content
                yield "chunk", content

        yield "final", (current_msg, current_think)

    except Exception as e:
        yield "error", e


# ==================== UI 状态更新 ====================


async def _update_thinking_ui(task: TelegramTaskItem, current_think: str) -> None:
    """更新思考中 UI"""
    current_time = asyncio.get_event_loop().time()

    if current_time - task.last_draft_time < ai_config.think_throttle_sec:
        return

    try:
        preview_think = _trim(current_think)

        if await task.is_deleted():
            raise AITaskStoppedError() from None

        # 仅私聊模式下更新草稿
        if task.type_ == ChatType.PRIVATE:
            success = await task.safe_draft(preview_think)
            if success:
                task.last_draft_time = current_time

    except TelegramRetryAfter as e:
        if (t := e.retry_after) > 0:
            logger.error(f"触发频控，等待 {t} 秒...")
            await asyncio.sleep(t)


async def _update_final_ui(
    task: TelegramTaskItem, final_think: str, has_error: bool
) -> None:
    """更新最终 UI"""
    try:
        if has_error:
            final_display_text = "思考中断"
            logger.error("思考中断")
        else:
            preview_think = _trim(final_think)
            final_display_text = f"思考完成\n{preview_think}"

        if await task.is_deleted():
            raise AITaskStoppedError() from None

        if task.type_ == ChatType.PRIVATE:
            await task.safe_draft("\u061c")
        else:
            final_display_text = "\u061c"

        await task.safe_edit(final_display_text)
    except AITaskStoppedError:
        raise
    except Exception as e:
        logger.send_error("UI 更新失败", e)


# ==================== 最终回复发送 ====================


async def _send_final_reply(task: TelegramTaskItem, final_msg: str) -> None:
    """发送最终回复"""
    if len(final_msg) > ai_config.msg_chunk_size:
        await _send_long_message(task, final_msg)
    else:
        if task.type_ == ChatType.PRIVATE:
            await task.safe_reply(final_msg)
        else:
            await task.safe_edit(final_msg)


# ==================== 核心工作循环 ====================


async def worker_loop(task: TelegramTaskItem, user: str) -> None:
    """核心工作循环"""
    message = task.message
    text = message.text
    if text is None:
        logger.debug("消息无文本，跳过")
        return

    session = user_sessions[user]
    session.md_status = True
    task.draft_id = int(time.time_ns() % 2**63)
    task.last_draft_time = 0
    final_msg = final_think = ""
    has_error = False

    try:
        async for event_type, data in _handle_ai_message(user, text):
            match event_type:
                case "think":
                    await _update_thinking_ui(task, data)
                case "chunk":
                    pass
                case "final":
                    final_msg, final_think = data
                case "error":
                    logger.send_error("流式处理错误", data)
                    has_error = True

        await _update_final_ui(task, final_think, has_error)

        await _send_final_reply(task, final_msg)

        session.message.extend(
            [build_message("user", text), build_message("assistant", final_msg)]
        )

        await _save_conversation_record(user, text, final_msg, final_think)

    except AITaskStoppedError:
        raise
    except Exception as e:
        logger.send_error("Worker 运行时错误", e)
        await task.safe_reply(msgs.AI_UNAVAILABLE)
