# src/plugins/AI/services/_summary.py
"""上文压缩服务

- 后台协程把交来的问答压成摘要并写回会话
- 摘要超硬上限按句子边界裁掉前段
"""

from core.domain import ChatRole
from core.domain.ids import SessionKey
from core.dto import MessageDTO
from utils import get_logger

from ..config import ai_config
from ..core import AIClient, save_summary
from ..markdown import strip_model_marks
from ..utils import build_message, estimate_tokens, render_history

_logger = get_logger("Plg.AI.Summary")

# 压缩指令，发言人标注要求逐字照抄，压坏名称与 id 的对应不如不压
_COMPRESS_PROMPT = (
    "把下面的对话记录压成一段摘要，要求：\n"
    "1. 每处 [名称|id] 标注原样照抄，不改名、不并人、不编造\n"
    "2. 保留聊过的话题、给出的结论、没办完的事和出现过的数字\n"
    "3. 只输出摘要正文，纯文本，不加标题与任何样式标记，不作评价\n\n"
    "对话记录："
)

# 句子结束符，裁尾只在这些位置下刀
_SENTENCE_ENDS = "。！？!?\n"


async def compress_history(key: SessionKey, rows: tuple[MessageDTO, ...]) -> None:
    """压缩问答并写回摘要

    - 请求失败或返回空即保持原摘要不动
    - 落笔前先确认会话没被清掉
    - 异常只记录不外抛，不拖垮对话
    """
    text = render_history(rows)
    if not text:
        return

    try:
        summary = strip_model_marks((await _request_summary(text)).strip())
        if not summary:
            _logger.error(f"{key} 压缩返回空，保留原摘要")
            return
        if estimate_tokens(summary) > ai_config.summary_soft_limit:
            _logger.info(f"{key} 摘要超软阈值，考虑下调压缩触发线")
        written = await save_summary(key, _trim_summary(summary))
        if written:
            _logger.info(f"{key} 摘要已更新")
    except Exception as e:
        _logger.send_error(f"{key} 摘要压缩失败", e)


async def _request_summary(text: str) -> str:
    """发一次压缩请求并收全正文"""
    turns = [
        build_message(ChatRole.SYSTEM, _COMPRESS_PROMPT),
        build_message(ChatRole.USER, text),
    ]

    current = ""
    async for delta in AIClient.stream_chat(turns):
        if (content := delta.get("content")) is not None:
            current += content
    return current


def _trim_summary(text: str) -> str:
    """摘要超硬上限即丢掉前段留尾部

    - 按句子边界切，不留半句
    - 整段找不到边界时按体量比例硬切
    """
    limit = ai_config.summary_hard_limit
    while (size := estimate_tokens(text)) > limit:
        cut = _first_boundary(text)
        if cut is None:
            keep = max(len(text) * limit // size, 1)
            return text[-keep:]
        text = text[cut:]
    return text


def _first_boundary(text: str) -> int | None:
    """取首个句子结束位的下一字符下标"""
    found = [pos for pos in (text.find(end) for end in _SENTENCE_ENDS) if pos != -1]
    return None if not found else min(found) + 1
