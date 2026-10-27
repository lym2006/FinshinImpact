# src/utils/speaker.py
"""发言人标注帧

- 标注与引用帧是全链路唯一形状，日志与模型侧只差内容
- 标注与正文直接相接不留空格，引用块同样紧贴正文
- 显示名只留字母数字与间隔符，命中标记词即遮成星号
"""

import re
import unicodedata

from core.domain.ids import UserId

# 标注与引用帧，形状与随包人设 §二 逐字一致，改一处必改另一处
_MARK = "[{slot}]"
_QUOTE = "（引用 [{slot}]：{text}）"

# 机器人自身的标注位，不带 id
_ASSISTANT_SLOT = "assistant"

# 名称白名单：Unicode 认定的字母与数字留下，其余逐个去掉
_NAME_SEPARATORS = "·' -"  # 名称里合法的间隔符
_SPACE_RUN = re.compile(r"\s+")

# 标记词：名称里出现即遮成星号，比对先归一全角并跳过空白
_MARK_WORDS = ("assistant", "历史摘要", "引用")

# 遮位与连续遮位
_MASK = "*"
_MASK_RUN = re.compile(r"\*+")


def clean_name(name: str) -> str:
    """清洗显示名

    - 换行等空白先折成一个空格，字母数字与间隔符之外的字符逐个去掉
    - 命中标记词即遮成星号，整名只剩遮位即交空串
    - 清洗后为空即交空串，由调用侧退化成纯 id 段
    """
    folded = _SPACE_RUN.sub(" ", name)
    kept = "".join(c for c in folded if c.isalnum() or c in _NAME_SEPARATORS)
    return _mask_marks(_SPACE_RUN.sub(" ", kept).strip())


def _folded_form(name: str) -> tuple[str, list[int]]:
    """取比对用的折叠形，并记下每字在原串里的下标

    - 逐字归一全角并转小写，空白整个跳过
    """
    parts: list[str] = []
    origin: list[int] = []
    for index, char in enumerate(name):
        if char.isspace():
            continue
        folded = unicodedata.normalize("NFKC", char).lower()
        parts.append(folded)
        origin.extend([index] * len(folded))
    return "".join(parts), origin


def _mask_marks(cleaned: str) -> str:
    """遮掉名称里的标记词

    - 标记词被打散成空格或写成全角同样命中，整段连中间空白一起遮
    - 遮完只剩星号即交空串，等同于名称全是标记词
    """
    folded, origin = _folded_form(cleaned)
    spans = _mark_spans(folded, origin)
    if not spans:
        return cleaned
    masked = cleaned
    for left, right in sorted(spans, reverse=True):
        masked = f"{masked[:left]}{_MASK}{masked[right:]}"
    masked = _MASK_RUN.sub(_MASK, masked).strip()
    return "" if masked == _MASK else masked


def _mark_spans(folded: str, origin: list[int]) -> list[tuple[int, int]]:
    """标记词在原串里的起止下标"""
    spans: list[tuple[int, int]] = []
    for word in _MARK_WORDS:
        start = 0
        while (found := folded.find(word, start)) != -1:
            end = found + len(word) - 1
            spans.append((origin[found], origin[end] + 1))
            start = end + 1
    return spans


def _speaker_slot(user_id: UserId, display_name: str) -> str:
    """取标注方括号里的内容"""
    name = clean_name(display_name)
    return f"{name}|{user_id}" if name else str(user_id)


def speaker_mark(user_id: UserId, display_name: str) -> str:
    """拼发言人标注

    - 群聊与私聊同形，档位只由 id 段区分
    """
    return _MARK.format(slot=_speaker_slot(user_id, display_name))


def quote_block(user_id: UserId, display_name: str, text: str) -> str:
    """拼引用块

    - 无引用文字即整块省略
    """
    if not text:
        return ""
    return _QUOTE.format(slot=_speaker_slot(user_id, display_name), text=text)


def bot_quote_block(text: str) -> str:
    """拼引用机器人自身话语的引用块"""
    if not text:
        return ""
    return _QUOTE.format(slot=_ASSISTANT_SLOT, text=text)
