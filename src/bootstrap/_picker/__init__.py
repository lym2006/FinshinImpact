# src/bootstrap/_picker/__init__.py
"""实例选窗域门面

- 代发选择窗与启动提示卡入口供启动资格判定调用
"""

from ._launch import show_launch_wait
from ._window import pick_profile

__all__ = [
    # 选窗与提示卡
    "pick_profile",
    "show_launch_wait",
]
