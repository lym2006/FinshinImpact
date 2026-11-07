# src/ui/_guide/__init__.py
"""引导期窗体门面

- 代发选实例、启动提示卡、提示弹窗、插件面板与启动结算各入口
"""

from ._launch import show_launch_wait
from ._panel import MODE_AUTO, open_panel
from ._picker import pick_profile
from ._popup import show_popup
from ._startup import settle_runtime

__all__ = [
    # 选实例与启动提示
    "pick_profile",
    "show_launch_wait",
    "show_popup",
    # 插件面板与启动结算
    "open_panel",
    "MODE_AUTO",
    "settle_runtime",
]
