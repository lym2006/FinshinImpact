# src/core/contracts/__init__.py
"""契约门面

- 定义核心业务与外部平台、基础设施交互的契约
- 零实现，仅包含抽象接口与协议定义
"""

from ._adapter import InteractionPort

__all__ = [
    # 适配器
    "InteractionPort",
]
