# src/plugins/AI/core/models.py
"""核心数据模型（内部实现）

- 定义任务载体与会话状态结构
"""

from dataclasses import dataclass, field

from aiogram.types import Message

# ==================== 任务数据模型 ====================


@dataclass
class TaskItem:
    """任务数据载体（纯数据）"""

    message: Message
    chat_id: int
    ori_id: int  # 原始消息 ID
    type_: str  # 聊天类型（私聊、群组等）
    status_id: int = 0  # 状态消息 ID
    draft_id: int = 0  # 草稿消息 ID
    last_draft_time: float = 0.0  # 上次更新草稿时间


# ==================== 用户会话模型 ====================


@dataclass
class UserSession:
    """用户会话数据结构（纯数据）"""

    message: list[dict[str, str]] = field(default_factory=list)
    md_status: bool = False  # 是否有 Markdown 内容可以输出
    is_active: bool = False  # 当前会话是否处于活跃状态
    last_active: float = 0.0  # 最后一次活跃时间
