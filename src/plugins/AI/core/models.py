# src/plugins/AI/core/models.py
"""核心数据模型

- 定义任务载体与会话状态结构
"""

from dataclasses import dataclass, field

from aiogram.types import Message


@dataclass
class TaskItem:
    """任务数据载体"""

    message: Message
    chat_id: int
    ori_id: int  # 原始消息 ID
    type_: str  # 聊天类型（私聊、群组等）


@dataclass
class UserSession:
    """用户会话数据结构"""

    message: list[dict[str, str]] = field(default_factory=list)
    md_status: bool = False  # 是否有 Markdown 内容可以输出
    is_active: bool = False  # 当前会话是否处于活跃状态
    last_active: float = 0.0  # 最后一次活跃时间
