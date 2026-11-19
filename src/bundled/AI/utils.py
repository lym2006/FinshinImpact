"""AI 工具

- 消息构建与发言人标注拼装
- 会话窗口归一与人设版本判定
- 上下文体量折算，含每条消息的打包开销
"""

import re
import time

from finshin_sdk.domain import ChatRole, ContentKind
from finshin_sdk.domain.ids import KEY_SEP, SessionKey
from finshin_sdk.dto import InboundEventDTO, MessageDTO, PrincipalDTO
from utils.speaker import (
    bot_quote_block,
    link_mark,
    media_mark,
    quote_block,
    speaker_mark,
    summary_mark,
)

# 会话窗口条数上限，含人设首行，条数只当兜底
_MAX_CONTEXT_MESSAGES = 120

# 一轮问答入库的消息条数
_ROUND_ROWS = 2

# 问答行的类型别名，窗口切段与渲染共用
_Rows = tuple[MessageDTO, ...]

# 发往模型的消息列表类型别名，体量折算与打包开销倒推共用
_Turns = list[dict[str, str]]

# 字符折算系数，只折正文
_CN_TOKENS_PER_CHAR = 0.7
_OTHER_TOKENS_PER_CHAR = 0.35

# 汉字基本区上下界，即 U+4E00 与 U+9FFF
_HAN_LOW = "一"
_HAN_HIGH = "鿿"

# 网址形状，只认带协议的与 www 起头的，按 URI 合法字符收边
_URL_RUN = re.compile(r"(?:https?://|www\.)[A-Za-z0-9:/?#@!$&'*+,;=~.%_-]+")


def build_message(role: str, content: str) -> dict[str, str]:
    """构建 AI 消息字典

    - 角色：user / system / assistant
    """
    return {"role": role, "content": content}


def make_session_key(principal: PrincipalDTO) -> SessionKey:
    """取会话键

    - 键由平台与容器拼成
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


class _TurnOverhead:
    """每条消息的打包开销现值

    - 打包开销由端点回报的读数倒推
    - 没拿到过读数即按 0 算
    """

    def __init__(self) -> None:
        self.per_turn = 0

    def refresh(self, content: int, actual: int, turns: int) -> None:
        """刷新消息打包开销的折算值

        - 读数不大于正文折算时不更新现值
        """
        # 模型侧给每条消息还补一个角色记号，正文里看不见，只能从读数倒推
        if turns and actual > content:
            self.per_turn = (actual - content) // turns


_turn_overhead = _TurnOverhead()


def estimate_tokens(text: str) -> int:
    """按字符估算 token

    - 汉字与其余字符各按自己的系数折算
    """
    han = sum(1 for char in text if _HAN_LOW <= char <= _HAN_HIGH)
    other = len(text) - han
    return int(han * _CN_TOKENS_PER_CHAR + other * _OTHER_TOKENS_PER_CHAR)


def _estimate_turns(turns: _Turns) -> int:
    """按实际发出的消息列表折算上下文体量

    - 正文逐条折算，再按条数补现值定的打包开销
    """
    return _content_tokens(turns) + len(turns) * _turn_overhead.per_turn


def learn_turn_overhead(turns: _Turns, actual: int) -> None:
    """用端点读数倒推每条消息的打包开销

    - 用读数扣掉正文折算得到打包开销
    """
    _turn_overhead.refresh(_content_tokens(turns), actual, len(turns))


def estimate_window(window: _Rows, summary: str, prompt: str) -> int:
    """估算一轮请求的上下文体量

    - 按实际发出的那份消息列表折算，人设与摘要一并计入
    """
    return _estimate_turns(
        build_turns(
            persona=window[0].content,
            summary=summary,
            history=window[1:],
            thisinput=prompt,
        )
    )


def _content_tokens(turns: _Turns) -> int:
    """逐条折算消息正文"""
    return sum(estimate_tokens(turn["content"]) for turn in turns)


def render_history(rows: _Rows) -> str:
    """渲染交模型压缩的问答文本

    - 发言人标注逐字带上
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
    - 发给模型的正文与摘要里的网址换成占位标记
    """
    turns = [build_message(ChatRole.SYSTEM, persona)]
    if summary:
        turns.append(
            build_message(ChatRole.USER, f"{summary_mark()} {_strip_links(summary)}")
        )

    turns.extend(
        _render_turn(message) for message in history if message.role != ChatRole.SYSTEM
    )
    turns.append(build_message(ChatRole.USER, _strip_links(thisinput)))
    return turns


def _render_turn(message: MessageDTO) -> dict[str, str]:
    """构建单条历史轮

    - 发言人标注按库里两列现拼，AI 回复不带标注
    """
    if message.role == ChatRole.ASSISTANT:
        return build_message(message.role, message.content)
    mark = speaker_mark(message.sender_id, message.sender_name)
    return build_message(message.role, f"{mark}{_strip_links(message.content)}")


def _strip_links(text: str) -> str:
    """把正文里的网址换成占位标记"""
    return _URL_RUN.sub(link_mark(), text)


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

    - 引用块加占位帧加裸正文
    """
    return f"{_quote_block(event)}{_body_text(event)}"


def _body_text(event: InboundEventDTO) -> str:
    """这条事件自己的正文

    - 带附文的媒体把种类标记打在前头，没附文的纯图算没正文
    """
    if not event.content.text:
        return ""
    kinds = dict.fromkeys(entry.kind for entry in event.content.media)
    marks = "".join(media_mark(kind) for kind in kinds)
    return f"{marks}{event.content.text}"


def _quote_block(event: InboundEventDTO) -> str:
    """拼引用块

    - 被引的是机器人自身即只写 assistant 位，不带 id
    - 种类顶在引文之前，与问句正文同形
    """
    kind_mark = (
        "" if event.reply_kind == ContentKind.TEXT else media_mark(event.reply_kind)
    )
    quoted = f"{kind_mark}{event.reply_text}"
    if not quoted:
        return ""
    if event.reply_to_bot:
        return bot_quote_block(quoted)
    return quote_block(event.reply_sender_id, event.reply_sender_name, quoted)
