# src/plugins/AI/services/worker.py
"""对话工作循环

- 实现流式接收、会话落库与记录持久化
"""

import asyncio
import time
from collections.abc import AsyncGenerator
from typing import Any, Literal

from exceptions import MessageVanishedError
from services.context import HandlerContext
from utils import get_logger

from ...messages import BotMessage
from ..config import ai_config
from ..core import AIClient, read_session, save_session
from ..utils import (
    build_turns,
    compose_user_text,
    make_rows,
    make_session_key,
    open_window,
)

_logger = get_logger("Plg.AI.Worker")


def _save_conversation_record(stem: str, text: str, final_msg: str) -> None:
    """写入对话记录

    - 落盘失败只记错误，不影响本轮应答
    - 走线程落盘，磁盘慢不冻事件循环
    """
    wrt = (
        f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}\n\n"
        f"用户：{text}\n\n"
        f"AI回复：\n{final_msg}\n\n\n"
    )
    try:
        with open(ai_config.record_dir / f"temp/{stem}.md", "a", encoding="utf8") as f:
            f.write(wrt)
    except Exception as e:
        _logger.send_error("保存本地对话记录失败", e)


async def _handle_ai_message(
    msg: list[dict[str, str]],
) -> AsyncGenerator[tuple[Literal["final", "error"], Any], None]:
    """处理 AI 流式数据

    - 产出 (事件类型, 数据)
    """
    current_msg = ""

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


async def worker_loop(ctx: HandlerContext) -> None:
    """核心工作循环"""
    text = ctx.event.content.text
    if not text:
        _logger.debug("消息无文本，跳过")
        return

    # 任务开始前探一次，原消息已删即中断，不持续轮询
    if not await ctx.interaction.probe_existence(ctx.event.ref):
        raise MessageVanishedError(ctx.event.ref)

    stem = ctx.event.principal.key
    session_key = make_session_key(ctx.event.principal)
    snapshot = await read_session(session_key)

    # 人设轮每轮按当前配置与磁盘正文重取，库里那行人设正文只当版本标记
    persona = ai_config.init[0]["content"]
    window = open_window(persona, snapshot.messages)
    final_msg = ""
    has_error = False

    # 落盘记录存裸正文，标注只进发给模型的轮次
    prompt = compose_user_text(ctx.event)
    msg = build_turns(
        persona=persona,
        summary=snapshot.summary,
        history=window[1:],
        scope=ctx.event.scope,
        thisinput=prompt,
    )

    try:
        async for event_type, data in _handle_ai_message(msg):
            match event_type:
                case "final":
                    final_msg = data
                case "error":
                    _logger.send_error("流式处理错误", data)
                    has_error = True

        if has_error or not final_msg:
            await ctx.reply(BotMessage.AI_UNAVAILABLE)
            return

        # 分段与防频控归适配层端口，此处只交整段正文
        await ctx.reply(final_msg)

        await save_session(session_key, (*window, *make_rows(ctx.event, final_msg)))

        await asyncio.to_thread(_save_conversation_record, stem, text, final_msg)

    except MessageVanishedError:
        raise
    except Exception as e:
        _logger.send_error("Worker 运行时错误", e)
        await ctx.reply(BotMessage.AI_UNAVAILABLE)
