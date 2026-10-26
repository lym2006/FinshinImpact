# src/plugins/AI/services/worker.py
"""对话工作循环

- 实现流式接收、会话落库与记录持久化
- 上下文超线即裁窗并投递后台压缩
"""

import asyncio
import time
from collections.abc import AsyncGenerator
from typing import Any, Literal

from core.domain import ChatScope
from core.domain.ids import SessionKey
from core.dto import InboundEventDTO, MessageDTO
from exceptions import DomainError, MessageVanishedError
from services.context import HandlerContext
from utils import get_logger

from ...messages import BotMessage
from ..config import ai_config
from ..core import (
    AIClient,
    StreamUsage,
    active_tasks,
    purge_history,
    read_session,
    save_session,
)
from ..markdown import strip_model_marks
from ..utils import (
    build_turns,
    compose_user_text,
    estimate_window,
    make_rows,
    make_session_key,
    matches_persona,
    open_window,
    speaker_mark,
    split_rounds,
)
from ._summary import compress_history

_logger = get_logger("Plg.AI.Worker")


def _save_conversation_record(
    key: SessionKey, event: InboundEventDTO, final_msg: str
) -> None:
    """写入对话记录

    - 一群一份、一私聊一份，条目内注明发言人
    - 落盘记录不含引用块，只存发言人与裸正文
    - 落盘失败只记错误，不影响本轮应答
    - 走线程落盘，磁盘慢不冻事件循环
    """
    speaker = speaker_mark(event.scope, event.principal.user, event.display_name)
    wrt = (
        f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}\n\n"
        f"{speaker}：{event.content.text}\n\n"
        f"AI回复：\n{final_msg}\n\n\n"
    )
    try:
        with open(ai_config.record_dir / f"{key}.md", "a", encoding="utf8") as f:
            f.write(wrt)
    except Exception as e:
        _logger.send_error("保存本地对话记录失败", e)


async def _handle_ai_message(
    msg: list[dict[str, str]], usage: StreamUsage
) -> AsyncGenerator[tuple[Literal["final", "error"], Any], None]:
    """处理 AI 流式数据

    - 产出 (事件类型, 数据)
    - 端点回的 token 读数随流写入读数容器
    """
    current_msg = ""

    try:
        async for delta in AIClient.stream_chat(msg, usage):
            # 处理正文内容
            if (content := delta.get("content")) is not None:
                if content.startswith("\n\n"):
                    content = content[2:]
                current_msg += content
        yield "final", current_msg
    except Exception as e:
        yield "error", e


async def _collect_reply(
    turns: list[dict[str, str]], key: SessionKey, tokens: int
) -> tuple[str, bool]:
    """收全一轮应答

    - 交出正文与是否出错
    - 端点报的输入 token 数与字符估并排记一行，裁窗判据照旧走字符估
    """
    final_msg = ""
    has_error = False
    usage = StreamUsage()
    async for event_type, data in _handle_ai_message(turns, usage):
        match event_type:
            case "final":
                final_msg = data
            case "error":
                _logger.send_error("流式处理错误", data)
                has_error = True
    if usage.prompt_tokens is not None:
        _logger.info(f"{key} 上下文估算 {tokens}，端点报 {usage.prompt_tokens}")
    return final_msg, has_error


def _kick_compression(
    key: SessionKey, scope: ChatScope, head: tuple[MessageDTO, ...], tokens: int
) -> None:
    """投递后台压缩协程

    - 压缩不落对话队列，跟用户命令不抢同一条语义
    """
    _logger.info(f"{key} 上下文 {tokens} token 超线，交后台压缩")
    summary_task = asyncio.create_task(compress_history(key, scope, head))
    active_tasks.add(summary_task)
    summary_task.add_done_callback(active_tasks.discard)


def _cut_for_budget(
    window: tuple[MessageDTO, ...], summary: str, prompt: str
) -> tuple[tuple[MessageDTO, ...], tuple[MessageDTO, ...], int]:
    """按 token 触发线裁窗

    - 交出裁过的窗口、待压段与体量估算
    - 没超线窗口一字不动，待压段为空
    """
    tokens = estimate_window(window, summary, prompt)
    if tokens <= ai_config.summary_trigger_tokens:
        return window, (), tokens
    head, rows = split_rounds(window[1:], ai_config.summary_keep_rounds)
    return (window[0], *rows), head, tokens


async def worker_loop(ctx: HandlerContext) -> None:
    """核心工作循环"""
    text = ctx.event.content.text
    if not text:
        _logger.debug("消息无文本，跳过")
        return

    # 任务开始前探一次，原消息已删即中断，不持续轮询
    if not await ctx.interaction.probe_existence(ctx.event.ref):
        raise MessageVanishedError(ctx.event.ref)

    session_key = make_session_key(ctx.event.principal)
    snapshot = await read_session(session_key)

    # 人设轮每轮按当前配置与磁盘正文重取，库里那行人设正文只当版本标记
    persona = ai_config.init[0]["content"]

    # 库里的人设版本对不上即换过人设或主人，所有人的记录连带库一起清
    if snapshot.messages and not matches_persona(persona, snapshot.messages):
        await purge_history()
        snapshot = await read_session(session_key)

    window = open_window(persona, snapshot.messages)
    prompt = compose_user_text(ctx.event)

    # 超线当轮即裁到保留窗口照常发出，被裁的问答交后台压成摘要，用户不等待
    window, head, tokens = _cut_for_budget(window, snapshot.summary, prompt)

    msg = build_turns(
        persona=persona,
        summary=snapshot.summary,
        history=window[1:],
        scope=ctx.event.scope,
        thisinput=prompt,
    )

    try:
        final_msg, has_error = await _collect_reply(msg, session_key, tokens)
        if has_error or not final_msg:
            await ctx.reply(BotMessage.AI_UNAVAILABLE)
            return

        # 漏网样式在入库前洗掉，发出、落记录与回喂模型的三路拿到的都是纯文本
        final_msg = strip_model_marks(final_msg)

        # 分段与防频控归适配层端口，此处只交整段正文
        await ctx.reply(final_msg)

        await save_session(session_key, (*window, *make_rows(ctx.event, final_msg)))

        await asyncio.to_thread(
            _save_conversation_record, session_key, ctx.event, final_msg
        )

        if head:
            _kick_compression(session_key, ctx.event.scope, head, tokens)

    except DomainError:
        raise
    except Exception as e:
        _logger.send_error("Worker 运行时错误", e)
        await ctx.reply(BotMessage.AI_UNAVAILABLE)
