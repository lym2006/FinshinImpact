# src/ui/_bridge/__init__.py
"""信号桥子包门面

- 代发 bot↔GUI 共用的单例桥梁
"""

from ._mediator import gui_bridge

__all__ = [
    # 单例桥梁
    "gui_bridge",
]
