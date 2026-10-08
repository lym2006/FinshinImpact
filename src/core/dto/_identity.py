# src/core/dto/_identity.py
"""身份数据传输对象

- 定义会话主体与消息定位
"""

from dataclasses import dataclass

from ..domain import Platform
from ..domain.ids import Container, MessageId, MessageKey, PrincipalKey, UserId


@dataclass(frozen=True, slots=True)
class PrincipalDTO:
    """会话主体标识"""

    platform: Platform
    container: Container
    user: UserId

    @property
    def key(self) -> PrincipalKey:
        """全局唯一键

        - 形如
            - tg:g100123:456
            - qq:u123:123
        """
        return PrincipalKey(f"{self.platform}:{self.container}:{self.user}")


@dataclass(frozen=True, slots=True)
class MsgReferenceDTO:
    """消息定位三元组

    - 图片定位接口的寻址依据
    """

    platform: Platform
    container: Container
    message_id: MessageId

    @property
    def key(self) -> MessageKey:
        """三元组联合键"""
        return MessageKey(f"{self.platform}:{self.container}:{self.message_id}")
