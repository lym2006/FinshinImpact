# src/ui/_lifecycle/__init__.py
"""哑运行时子包门面

- 代发应用实例与计时泵
"""

from ._app import ensure_app
from ._ticker import Ticker

__all__ = [
    # 应用实例
    "ensure_app",
    # 计时泵
    "Ticker",
]
