# src/bot/_adapter_host/__init__.py
"""适配器装载门面

- 代发上层按平台标识取适配器四件
"""

from ._parts import parts_for

__all__ = [
    # 取件
    "parts_for",
]
