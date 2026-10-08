# src/core/domain/_content.py
"""内容值对象

- 定义跨平台归一的内容类型词表
"""

from enum import StrEnum


class ContentKind(StrEnum):
    """内容类型"""

    TEXT = "text"
    PHOTO = "photo"
    DOCUMENT = "document"
    AUDIO = "audio"
    VOICE = "voice"
    ANIMATION = "animation"
    VIDEO = "video"
    UNKNOWN = "unknown"
