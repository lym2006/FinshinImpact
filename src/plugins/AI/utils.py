# src/plugins/AI/utils.py
"""AI 工具

- 提供消息构建与发言人标注拼装
- 定义退避重试装饰器
"""

import functools
from collections.abc import Callable
from typing import TYPE_CHECKING, ParamSpec, TypeVar

from aiogram.exceptions import TelegramNetworkError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from core.domain import ChatScope
from core.dto import InboundEventDTO
from utils import get_logger

if TYPE_CHECKING:
    from .core.models import UserSession

_logger_retry = get_logger("Plg.AI.Retry")

# 泛型定义
P = ParamSpec("P")
T = TypeVar("T")

# 重试器
_MAX_RETRIES = 3
_MIN_RETRY_DELAY = 1
_MAX_RETRY_DELAY = 10

# 发给模型的内部标记，格式与随包人设 §二 逐字一致，改一处必改另一处
_GROUP_MARK = "[{name} | {id}] "
_PRIVATE_MARK = "[{id}] "
_GROUP_QUOTE = "（引用 [{name} | {id}]：{text}）"
_PRIVATE_QUOTE = "（引用 [{id}]：{text}）"
_SUMMARY_MARK = "[历史摘要] "


def build_message(role: str, content: str) -> dict[str, str]:
    """构建 AI 消息字典

    - 角色：user / system / assistant
    """
    return {"role": role, "content": content}


def make_data(session: "UserSession", thisinput: str) -> list[dict[str, str]]:
    """构建包含新输入的用户消息数据列表

    - 摘要作独立 system 轮排在人设之后
    """
    turns = session.message + [build_message("user", thisinput)]
    if not session.summary:
        return turns
    summary_round = build_message("system", f"{_SUMMARY_MARK}{session.summary}")
    # 首位恒为人设 system 轮，建会话与 /clear 都以 ai_config.init 起头
    return [turns[0], summary_round, *turns[1:]]


def compose_user_text(event: InboundEventDTO) -> str:
    """拼发给 AI 的 user 轮正文

    - 顺序为发言人标注、引用块、正文
    - 落盘记录用裸正文，不带这些标记
    """
    if event.scope is ChatScope.PRIVATE:
        mark = _PRIVATE_MARK.format(id=event.principal.user)
    else:
        mark = _GROUP_MARK.format(
            # 名称缺位用 id 段填，格式仍是 [名称 | id]
            name=event.display_name or event.principal.user,
            id=event.principal.user,
        )
    return f"{mark}{_quote_block(event)}{event.content.text}"


def _quote_block(event: InboundEventDTO) -> str:
    """拼引用块

    - 无引用文字即整块省略
    """
    if not event.reply_text:
        return ""
    if event.scope is ChatScope.PRIVATE:
        return _PRIVATE_QUOTE.format(id=event.reply_sender_id, text=event.reply_text)
    return _GROUP_QUOTE.format(
        name=event.reply_sender_name or event.reply_sender_id,
        id=event.reply_sender_id,
        text=event.reply_text,
    )


def retry_sending() -> Callable[[Callable[P, T]], Callable[P, T]]:
    """消息发送重试装饰器

    - 网络异常时指数退避重试
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        @retry(
            retry=retry_if_exception_type(TelegramNetworkError),
            stop=stop_after_attempt(_MAX_RETRIES),
            wait=wait_exponential(min=_MIN_RETRY_DELAY, max=_MAX_RETRY_DELAY),
            before_sleep=lambda retry_state: _logger_retry.error(
                f"消息发送失败，正在第 {retry_state.attempt_number} 次重试..."
            ),
            reraise=True,
        )
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            return func(*args, **kwargs)

        return wrapper

    return decorator
