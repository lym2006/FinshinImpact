# src/plugins/AI/core/models.py
"""核心数据模型

- 定义容器级会话活跃时间结构
"""

from dataclasses import dataclass


@dataclass
class SessionState:
    """容器会话的活跃时间"""

    last_active: float = 0.0  # 闲置清理按它判到期
