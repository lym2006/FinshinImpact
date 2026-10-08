# src/core/domain/_platform.py
"""平台与会话值对象

- 定义跨平台归一的分类词表
- 定义实例身份码与平台的双向转换
"""

from enum import StrEnum


class Platform(StrEnum):
    """平台标识"""

    TELEGRAM = "tg"
    QQ = "qq"


class ChatScope(StrEnum):
    """会话作用域

    - 平台语义在此归一
    """

    PRIVATE = "private"
    GROUP = "group"
    UNKNOWN = "unknown"


# 实例身份码

# 身份码分隔符，平台前缀与账号 id 的唯一分界
_PROFILE_CODE_SEP = "-"


def make_profile_code(platform: Platform, account_id: str) -> str:
    """拼装实例身份码

    - 平台值本身即前缀，账号 id 为机器人在该平台的数字 ID
    """
    return f"{platform}{_PROFILE_CODE_SEP}{account_id}"


def platform_of_profile(code: str) -> Platform | None:
    """从身份码解析平台

    - partition 恒返三段，无分隔符时首段即整串，不越界
    - 前缀不是已知平台返回 None，回落策略由调用方决定
    """
    prefix = code.partition(_PROFILE_CODE_SEP)[0]
    try:
        return Platform(prefix)
    except ValueError:
        return None
