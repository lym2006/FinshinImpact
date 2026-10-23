# src/plugins/AI/core/models.py
"""核心数据模型

- 定义会话并发状态结构
"""

from dataclasses import dataclass


@dataclass
class SessionState:
    """会话并发状态"""

    is_active: bool = False  # 当前会话是否处于活跃状态
    last_active: float = 0.0  # 最后一次活跃时间
