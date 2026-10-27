# src/core/domain/_container.py
"""容器段归一

- 定义平台 id 到容器键的转换规则
"""

from ._platform import ChatScope
from .ids import ChatId, ContainerKey, UserId


def make_container(scope: ChatScope, chat_id: ChatId, user_id: UserId) -> ContainerKey:
    """归一容器段

    - 群聊 g 前缀加 chat_id 绝对值
    - 私聊 u 前缀加 user_id
    """
    match scope:
        case ChatScope.GROUP:
            return ContainerKey(f"g{abs(int(chat_id))}")  # 非法格式不能静默通过
        case ChatScope.PRIVATE:
            return ContainerKey(f"u{user_id}")
        case _:
            return ContainerKey("")
