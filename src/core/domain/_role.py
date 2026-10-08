# src/core/domain/_role.py
"""角色对象

- 定义跨平台归一的 AI 对话角色和用户权限角色
"""

from enum import IntEnum, StrEnum


class ChatRole(StrEnum):
    """AI 对话角色"""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class CommandRole(IntEnum):
    """用户权限角色

    - 值越小权限越高
    """

    OWNER = 0
    ADMIN = 10
    MEMBER = 50
