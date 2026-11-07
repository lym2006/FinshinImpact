# src/bot/_adapter_host/__init__.py
"""适配器装载门面

- 代发上层按平台标识取件与装配
"""

from ._assemble import assemble_platform
from ._parts import parts_for

__all__ = [
    # 取件
    "parts_for",
    # 装配
    "assemble_platform",
]
