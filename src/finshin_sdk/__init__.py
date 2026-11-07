# src/finshin_sdk/__init__.py
"""适配器接口门面

- 代发平台侧必须实现的两份抽象接口
"""

from ._adapter import BaseAdapter, InteractionPort

__all__ = [
    # 适配器
    "InteractionPort",
    "BaseAdapter",
]
