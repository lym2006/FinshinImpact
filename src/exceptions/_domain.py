# src/exceptions/_domain.py
"""领域异常族

- 定义业务逻辑异常
"""

from typing import TYPE_CHECKING

from ._base import BotError

if TYPE_CHECKING:
    from core.dto import MsgReferenceDTO


class DomainError(BotError):
    """领域异常基类"""


class MessageVanishedError(DomainError):
    """消息不存在

    - 被撤回或删除
    """

    def __init__(self, ref: "MsgReferenceDTO") -> None:
        self.platform = ref.platform
        self.message_id = ref.message_id
        super().__init__()


class TaskAbortedError(DomainError):
    """任务被主动终止"""


class PrincipalNotFoundError(DomainError):
    """未找到用户或群组"""
