# src/plugins/AI/core/utils.py
"""
AI 核心通用工具

提供：
- AI 消息数据构建工具
- 用户唯一身份标识提取
- 消息发送指数退避重试装饰器
"""

import functools
import logging
from collections.abc import Callable
from typing import ParamSpec, TypeVar

from aiogram.exceptions import TelegramNetworkError
from aiogram.types import Message
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .models import UserSession

logger_retry = logging.getLogger("Bot.Plugins.AI.Retry")

# ==================== 1. 全局配置与泛型定义 ====================
P = ParamSpec("P")
T = TypeVar("T")


# ==================== 2. 消息构建工具 ====================
def build_message(role: str, content: str) -> dict[str, str]:
    """构建发送给 AI 的消息字典

    Args:
        role: 消息角色，可选 "user"、"system" 、"assistant"
        content: 具体的文本内容

    Returns:
        包含角色和内容的标准化消息字典
    """
    return {"role": role, "content": content}


def make_data(session: UserSession, thisinput: str) -> list[dict[str, str]]:
    """构建包含新输入的用户消息数据列表

    Args:
        session: 用户的独立会话池
        thisinput: 当次的用户输入文本

    Returns:
        追加了新消息后的完整消息列表
    """
    return session.message + [build_message("user", thisinput)]


# ==================== 3. 用户信息提取 ====================
def get_name(message: Message) -> str:
    """获取用户的唯一身份标识

    Returns:
        用户身份标识，格式为 u_{user_id}（私聊）或 g_{group_id}_{user_id}（群聊）
    """
    id_ = message.chat.id
    return (
        f"g_{abs(id_)}_{getattr(getattr(message, 'from_user', None), 'id', 'unknown')}"
        if id_ < 0
        else f"u_{id_}"
    )


# ==================== 4. 异步重试装饰器 ====================
def retry_sending(max_retries: int = 3) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """消息发送重试装饰器工厂

    用于包装 Telegram 消息发送逻辑，在遇到网络异常时自动进行指数退避重试。

    Args:
        max_retries: 最大重试次数，默认为 3 次

    Returns:
        配置好的重试装饰器实例
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        @retry(
            retry=retry_if_exception_type(TelegramNetworkError),
            stop=stop_after_attempt(max_retries),
            wait=wait_exponential(multiplier=1, max=10, min=1),
            before=lambda retry_state: (
                logger_retry.warning(
                    f"🚨 消息发送失败，正在第 {retry_state.attempt_number - 1} 次重试..."
                )
                if retry_state.attempt_number > 1
                else None
            ),
            reraise=True,
        )
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            return func(*args, **kwargs)

        return wrapper

    return decorator
