# src/plugins/AI/services/worker.py
"""
AI 工作循环服务

负责：
- 协调流式数据接收
- 实时 UI 状态更新
- 对话记录持久化
"""

import asyncio
import logging
import time
from collections.abc import AsyncGenerator
from typing import Any

from aiogram.enums import ChatType
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter

from ..core import (
    AIClient,
    TaskStoppedError,
    TelegramTaskItem,
    build_message,
    make_data,
    user_sessions,
)
from ..core.config import RECORD_DIR
from .render import render_html, screenshot

logger = logging.getLogger("Bot.Plugins.AI.Worker")

# ==================== 常量配置 ====================
MSG_CHUNK_SIZE = 4000  # 单条消息最大字符数（Telegram 限制为 4096，留点余量）
FLOOD_THRESHOLD = 5  # 触发防频控休眠的总段数阈值
THINK_THROTTLE_SEC = 1.2  # 思考过程 UI 更新节流时间（秒）
TRIM_PREVIEW_LEN = 2000  # 思考预览文本的最大裁剪长度

# AI 对话接口配置（官方公开文档）
BASE_URL = "https://api.siliconflow.cn/v1"  # AI 对话接口根地址
REQUEST_PATH = "/chat/completions"  # AI 对话接口请求路径


# ==================== 1. 内部辅助函数 ====================
def _trim(text: str) -> str:
    """裁剪长文本，防止 Telegram 消息过长发送失败"""
    return text[-TRIM_PREVIEW_LEN:] if len(text) > TRIM_PREVIEW_LEN else text


async def _send_long_message(task: TelegramTaskItem, text: str) -> None:
    """分段发送长消息，并内置防频控机制"""
    total_len = len(text)
    total_chunks = (total_len + MSG_CHUNK_SIZE - 1) // MSG_CHUNK_SIZE

    for idx, i in enumerate(range(0, total_len, MSG_CHUNK_SIZE)):
        chunk = text[i : i + MSG_CHUNK_SIZE]
        try:
            await task.safe_reply(chunk)
        except TelegramBadRequest as e:
            logger.error(f"❌ 分段消息请求错误: {e}")
        except Exception as e:
            logger.error(f"❌ 分段消息未知错误: {e}")

        # 如果总段数超过阈值，且当前不是最后一段，则在发送后休眠防频控
        if total_chunks > FLOOD_THRESHOLD and idx < total_chunks - 1:
            await asyncio.sleep(1)


async def _save_conversation_record(
    user: str, text: str, final_msg: str, final_think: str
) -> None:
    """将对话记录异步写入本地文件 (HTML, TXT, MD)"""
    try:
        # 生成 HTML 并截图
        html_path = RECORD_DIR / f"temp/{user}.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(render_html(final_msg))
        await screenshot(user, str(html_path))

        # 格式化并写入 TXT 和 MD
        wrt = (
            f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}\n\n"
            f"用户：{text}\n\n"
            f"AI思考：\n{final_think}\n\n"
            f"AI回复：\n{final_msg}\n\n\n\n\n"
        )
        with open(RECORD_DIR / f"staged/{user}.txt", "a", encoding="utf8") as f:
            f.write(wrt)
        with open(RECORD_DIR / f"temp/{user}.md", "a", encoding="utf8") as f:
            f.write(wrt)
    except Exception as e:
        logger.error(f"❌ 保存本地对话记录失败: {e}")


# ==================== 2. 流式数据处理 ====================
async def _handle_ai_message(
    user: str, text: str
) -> AsyncGenerator[tuple[str, Any], None]:
    """处理 AI 流式返回数据

    Yields:
        tuple[str, Any]: (事件类型, 数据)
    """
    session = user_sessions[user]
    current_think = current_msg = ""
    msg = make_data(session, text)

    try:
        async for delta in AIClient.stream_chat(msg):
            logger.debug(f"🔍 流式返回的 delta: {delta}")

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
        logger.error(f"❌ 流式请求异常: {e}")
        yield "error", str(e)


# ==================== 3. UI 状态更新 ====================
async def _update_thinking_ui(task: TelegramTaskItem, current_think: str) -> None:
    """处理思考过程中的 UI 更新，内置节流与频控处理"""
    current_time = asyncio.get_event_loop().time()

    if current_time - task.last_draft_time < THINK_THROTTLE_SEC:
        return

    try:
        preview_think = _trim(current_think)

        if await task.is_deleted():
            raise TaskStoppedError()

        # 仅私聊模式下更新草稿
        if task.type_ == ChatType.PRIVATE:
            success = await task.safe_draft(preview_think)
            if success:
                task.last_draft_time = current_time

    except TelegramRetryAfter as e:
        if (t := e.retry_after) > 0:
            logger.warning(f"🚨 触发频控，等待 {t} 秒...")
            await asyncio.sleep(t)
    except Exception:
        raise


async def _update_final_ui(
    task: TelegramTaskItem, final_think: str, error_msg: str, has_error: bool
) -> None:
    """更新最终的 UI 状态 (思考完成 / 思考中断)"""
    try:
        if has_error:
            final_display_text = f"❌ 思考中断\n{error_msg}"
            logger.warning("🚨 思考中断")
        else:
            preview_think = _trim(final_think)
            final_display_text = f"✅ 思考完成\n{preview_think}"
            logger.info("🚀 正在推送最终思考内容...")

        if await task.is_deleted():
            raise TaskStoppedError() from None

        if task.type_ == ChatType.PRIVATE:
            await task.safe_draft("\u061c")
        else:
            final_display_text = "\u061c"

        await task.safe_edit(final_display_text)
    except TaskStoppedError:
        raise
    except Exception as e:
        logger.warning(f"🚨 UI 更新失败: {e}")


# ==================== 4. 最终回复发送 ====================
async def _send_final_reply(task: TelegramTaskItem, final_msg: str) -> None:
    """根据消息长度和聊天类型，发送最终的 AI 回复"""
    if len(final_msg) > MSG_CHUNK_SIZE:
        await _send_long_message(task, final_msg)
    else:
        try:
            if task.type_ == ChatType.PRIVATE:
                await task.safe_reply(final_msg)
            else:
                await task.safe_edit(final_msg)
        except Exception:
            raise


# ==================== 5. 核心工作循环 ====================
async def worker_loop(task: TelegramTaskItem, user: str) -> None:
    """核心工作循环，负责协调流式数据、UI 更新和记录保存"""
    message = task.message
    text = message.text
    if text is None:
        logger.warning("🚨 没有文本")
        return

    session = user_sessions[user]
    session.md_status = True
    task.draft_id = int(time.time_ns() % 2**63)
    task.last_draft_time = 0
    error_msg = final_msg = final_think = ""
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
                    logger.error(f"❌ 流式处理错误: {data}")
                    has_error = True
                    error_msg = data

        await _update_final_ui(task, final_think, error_msg, has_error)

        await _send_final_reply(task, final_msg)

        session.message.extend(
            [build_message("user", text), build_message("assistant", final_msg)]
        )

        await _save_conversation_record(user, text, final_msg, final_think)

    except TaskStoppedError:
        raise
    except Exception as e:
        logger.error(f"❌ Worker 运行时错误: {e}")
        await task.safe_reply("❌ AI 对话服务暂不可用")
