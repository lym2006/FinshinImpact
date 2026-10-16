# src/adapters/telegram/_errors.py
"""平台异常翻译

- 把 Telegram 错误串归一为领域异常
"""

from aiogram.exceptions import TelegramAPIError

from core.dto import MsgReferenceDTO
from exceptions import MessageVanishedError

# 服务端表示消息已不存在的错误串
_VANISHED_MARKS = (
    "message to edit not found",
    "message to be replied not found",
    "message_invalid_id",
)


def is_vanished(exc: TelegramAPIError) -> bool:
    """判定是否为消息已删除错误"""
    text = str(exc).lower()
    return any(mark in text for mark in _VANISHED_MARKS)


def translate(exc: TelegramAPIError, ref: MsgReferenceDTO) -> Exception:
    """翻译平台异常

    - 命中已删除标记返回消息不存在
    - 其余原样返回交调用方上抛
    """
    if is_vanished(exc):
        return MessageVanishedError(ref)
    return exc
