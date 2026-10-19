# src/plugins/AI/utils.py
"""AI 工具（内部实现）

- 提供消息构建与身份提取
- 定义退避重试装饰器
"""

import functools
from collections.abc import Callable
from typing import TYPE_CHECKING, ParamSpec, TypeVar

from aiogram.exceptions import TelegramNetworkError
from aiogram.types import Message
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from utils import get_logger

if TYPE_CHECKING:
    from .core.models import UserSession

logger_retry = get_logger("Plg.AI.Retry")
__all__ = [
    "build_message",
    "make_data",
    "get_name",
    "retry_sending",
]

# ==================== 内部常量与泛型定义 ====================

P = ParamSpec("P")
T = TypeVar("T")
_MAX_RETRIES = 3  # 重试器硬编码配置
_MIN_RETRY_DELAY = 1
_MAX_RETRY_DELAY = 10


# ==================== 消息构建工具 ====================


def build_message(role: str, content: str) -> dict[str, str]:
    """构建 AI 消息字典

    角色：user / system / assistant。
    """
    return {"role": role, "content": content}


def make_data(session: "UserSession", thisinput: str) -> list[dict[str, str]]:
    """构建包含新输入的用户消息数据列表"""
    return session.message + [build_message("user", thisinput)]


# ==================== 用户信息提取 ====================


def get_name(message: Message) -> str:
    """用户唯一标识

    格式 u_{id}（私聊）/ g_{群}_{id}（群聊）。
    """
    id_ = message.chat.id
    return (
        f"g_{abs(id_)}_{getattr(getattr(message, 'from_user', None), 'id', 'unknown')}"
        if id_ < 0
        else f"u_{id_}"
    )


# ==================== 异步重试装饰器 ====================


def retry_sending() -> Callable[[Callable[P, T]], Callable[P, T]]:
    """消息发送重试装饰器

    网络异常时指数退避重试。
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        @retry(
            retry=retry_if_exception_type(TelegramNetworkError),
            stop=stop_after_attempt(_MAX_RETRIES),
            wait=wait_exponential(min=_MIN_RETRY_DELAY, max=_MAX_RETRY_DELAY),
            before_sleep=lambda retry_state: logger_retry.error(
                f"消息发送失败，正在第 {retry_state.attempt_number} 次重试..."
            ),
            reraise=True,
        )
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            return func(*args, **kwargs)

        return wrapper

    return decorator
