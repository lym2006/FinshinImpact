# src/ui/_windows/__init__.py
"""主窗与控制器门面

- 代发主窗装配入口、主窗口、断连计时观察器与控制器
"""

from ._assembly import create_gui
from ._controllers import (
    BaseController,
    SettingsController,
    ShutdownController,
    build_controllers,
)
from ._link_watcher import LinkWatcher
from ._main_window import BotGUI

__all__ = [
    # 主窗装配入口
    "create_gui",
    # 主窗与观察器
    "BotGUI",
    "LinkWatcher",
    # 控制器装配入口
    "build_controllers",
    # 控制器类型
    "BaseController",
    "SettingsController",
    "ShutdownController",
]
