# src/finshin_sdk/domain/_task.py
"""任务对象

- 定义跨平台归一的任务状态词表与动作名归属判定
"""

from enum import StrEnum

from ._role import ChatRole
from .ids import KEY_SEP

_ChatTurn = tuple[ChatRole, str]
TaskPayload = tuple[_ChatTurn, ...]


def is_own_action(kind: str, plugin_name: str) -> bool:
    """判定动作名属不属于这只插件名下

    - 形状是「插件名.动作」，前段必须等于插件名，尾段非空
    - 尾段内容平台不解释
    """
    head, sep, action = kind.partition(KEY_SEP)
    return bool(sep and action and head == plugin_name)


class TaskStatus(StrEnum):
    """任务状态"""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
