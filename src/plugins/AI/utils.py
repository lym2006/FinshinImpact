# src/plugins/AI/utils.py
"""AI 工具

- 提供消息构建与发言人标注拼装
- 定义会话窗口归一与人设版本判定
- 定义上下文体量的字符折算
"""

import time

from core.domain import ChatRole
from core.domain.ids import KEY_SEP, SessionKey
from core.dto import InboundEventDTO, MessageDTO, PrincipalDTO
from utils.speaker import bot_quote_block, quote_block, speaker_mark

# 会话窗口条数上限，含人设首行，条数只当兜底
_MAX_CONTEXT_MESSAGES = 120

# 一轮问答入库的消息条数
_ROUND_ROWS = 2

# 问答行的类型别名，窗口切段与渲染共用
_Rows = tuple[MessageDTO, ...]

# 字符折算系数，官方比例为汉字 0.6、其余 0.3
_CN_TOKENS_PER_CHAR = 0.6
_OTHER_TOKENS_PER_CHAR = 0.3

# 汉字基本区上下界，即 U+4E00 与 U+9FFF
_HAN_LOW = "一"
_HAN_HIGH = "鿿"

# 摘要轮的行首标记，格式与随包人设 §二 逐字一致，改一处必改另一处
_SUMMARY_MARK = "[历史摘要] "


def build_message(role: str, content: str) -> dict[str, str]:
    """构建 AI 消息字典

    - 角色：user / system / assistant
    """
    return {"role": role, "content": content}


def make_session_key(principal: PrincipalDTO) -> SessionKey:
    """取会话键

    - 键只到平台与容器两段，同群共用一串上下文
    """
    return SessionKey(f"{principal.platform}{KEY_SEP}{principal.container}")


def open_window(persona: str, history: _Rows, *, new_count: int = _ROUND_ROWS) -> _Rows:
    """归一会话窗口

    - 缺人设首行或人设正文换过即整串重起，只留人设行
    - 窗口连同人设行与新写入的条数一起算上限
    - 越过上限从头部成对丢最旧问答
    """
    kept = history[1:] if matches_persona(persona, history) else ()
    _, tail = _cut_oldest(kept, _MAX_CONTEXT_MESSAGES - 1 - new_count)
    return (MessageDTO(role=ChatRole.SYSTEM, content=persona), *tail)


def matches_persona(persona: str, history: _Rows) -> bool:
    """判定窗口首行存的是当前人设正文"""
    return (
        bool(history)
        and history[0].role == ChatRole.SYSTEM
        and history[0].content == persona
    )


def _cut_oldest(rows: _Rows, keep: int) -> tuple[_Rows, _Rows]:
    """从头部丢到只剩指定条数

    - 落点撞上答句时连答句一起丢，问答不留半截
    - 返回丢掉段与保留段
    """
    start = max(len(rows) - keep, 0)
    while start < len(rows) and rows[start].role == ChatRole.ASSISTANT:
        start += 1
    return rows[:start], rows[start:]


def split_rounds(rows: _Rows, keep_rounds: int) -> tuple[_Rows, _Rows]:
    """按保留轮数切窗口

    - 尾部留满指定轮数原文，更早的问答进丢掉段
    """
    return _cut_oldest(rows, keep_rounds * _ROUND_ROWS)


def estimate_tokens(text: str) -> int:
    """按字符估算 token

    - 汉字按 0.6 折算，其余字符按 0.3
    """
    han = sum(1 for char in text if _HAN_LOW <= char <= _HAN_HIGH)
    other = len(text) - han
    return int(han * _CN_TOKENS_PER_CHAR + other * _OTHER_TOKENS_PER_CHAR)


def estimate_window(window: _Rows, summary: str, prompt: str) -> int:
    """估算一轮请求的上下文体量

    - 人设行、摘要、历史问答与新问句逐段累加
    """
    total = estimate_tokens(summary) + estimate_tokens(prompt)
    return total + sum(estimate_tokens(message.content) for message in window)


def render_history(rows: _Rows) -> str:
    """渲染交模型压缩的问答文本

    - 发言人标注逐字带上，名称与 id 的对应关系原样进压缩请求
    """
    return "\n".join(
        _render_turn(message)["content"]
        for message in rows
        if message.role != ChatRole.SYSTEM
    )


def build_turns(
    *,
    persona: str,
    summary: str,
    history: tuple[MessageDTO, ...],
    thisinput: str,
) -> list[dict[str, str]]:
    """构建发给模型的消息列表

    - 人设轮按当前正文现取，库里那行人设不重复发
    - 摘要固定作第一条独立 user 轮紧跟人设，后面不配 assistant 回复
    """
    turns = [build_message(ChatRole.SYSTEM, persona)]
    if summary:
        turns.append(build_message(ChatRole.USER, f"{_SUMMARY_MARK}{summary}"))

    turns.extend(
        _render_turn(message) for message in history if message.role != ChatRole.SYSTEM
    )
    turns.append(build_message(ChatRole.USER, thisinput))
    return turns


def _render_turn(message: MessageDTO) -> dict[str, str]:
    """构建单条历史轮

    - 发言人标注按库里两列现拼，AI 回复不带标注
    """
    if message.role == ChatRole.ASSISTANT:
        return build_message(message.role, message.content)
    mark = speaker_mark(message.sender_id, message.sender_name)
    return build_message(message.role, f"{mark}{message.content}")


def make_rows(event: InboundEventDTO, reply: str) -> tuple[MessageDTO, MessageDTO]:
    """构建入库的两条消息

    - 问答各一条，发言人两列只挂在问句上
    """
    now = time.time()
    return (
        MessageDTO(
            role=ChatRole.USER,
            content=_compose_body(event),
            created_at=now,
            sender_id=event.principal.user,
            sender_name=event.display_name,
        ),
        MessageDTO(role=ChatRole.ASSISTANT, content=reply, created_at=now),
    )


def compose_user_text(event: InboundEventDTO) -> str:
    """拼发给 AI 的 user 轮正文

    - 顺序为发言人标注、引用块、正文
    """
    mark = speaker_mark(event.principal.user, event.display_name)
    return f"{mark}{_compose_body(event)}"


def _compose_body(event: InboundEventDTO) -> str:
    """拼入库正文

    - 引用块加裸正文，落盘记录只取其中的裸正文
    """
    return f"{_quote_block(event)}{event.content.text}"


def _quote_block(event: InboundEventDTO) -> str:
    """拼引用块

    - 被引的是机器人自身即只写 assistant 位，不带 id
    """
    if not event.reply_text:
        return ""
    if event.reply_to_bot:
        return bot_quote_block(event.reply_text)
    return quote_block(event.reply_sender_id, event.reply_sender_name, event.reply_text)
