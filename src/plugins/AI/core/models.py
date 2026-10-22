# src/plugins/AI/core/models.py
"""核心数据模型

- 定义会话状态结构
"""

from dataclasses import dataclass, field


@dataclass
class UserSession:
    """用户会话数据结构"""

    message: list[dict[str, str]] = field(default_factory=list)
    summary: str = ""  # 压缩摘要，发给 AI 时作独立 system 轮
    is_active: bool = False  # 当前会话是否处于活跃状态
    last_active: float = 0.0  # 最后一次活跃时间
