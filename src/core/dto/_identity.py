# src/core/dto/_identity.py
"""身份数据传输对象

- 定义会话主体与消息定位
"""

from dataclasses import dataclass

from ..domain import Platform, make_record_stem
from ..domain.ids import (
    ContainerKey,
    MessageId,
    MessageKey,
    PrincipalKey,
    RecordStem,
    UserId,
)


@dataclass(frozen=True, slots=True)
class PrincipalDTO:
    """会话主体标识"""

    platform: Platform
    container: ContainerKey
    user: UserId

    @property
    def key(self) -> PrincipalKey:
        """全局唯一键

        - 形如 tg:g100123:456 或 qq:u123:123
        """
        return PrincipalKey(f"{self.platform}:{self.container}:{self.user}")

    @property
    def record_stem(self) -> RecordStem:
        """落盘文件名主干

        - key 含冒号不能当文件名，主干由容器段与用户段派生
        """
        return make_record_stem(self.container, self.user)


@dataclass(frozen=True, slots=True)
class MsgReferenceDTO:
    """消息定位三元组

    - 图片定位接口的寻址依据
    """

    platform: Platform
    container: ContainerKey
    message_id: MessageId

    @property
    def key(self) -> MessageKey:
        """三元组联合键"""
        return MessageKey(f"{self.platform}:{self.container}:{self.message_id}")
