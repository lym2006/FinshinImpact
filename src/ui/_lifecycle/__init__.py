# src/ui/_lifecycle/__init__.py
"""哑运行时子包门面

- 代发应用实例、事件泵与计时泵
"""

from ._app import ensure_app, pump_events
from ._ticker import Ticker

__all__ = [
    # 应用实例与事件泵
    "ensure_app",
    "pump_events",
    # 计时泵
    "Ticker",
]
