# src/gui/controllers/__init__.py
"""控制器门面

- 提供自动实例化与契约打包
"""

from collections.abc import Callable
from typing import TYPE_CHECKING

from ._base import BaseController
from ._dashboard import DashboardController
from ._proxy import ProxyController
from ._settings import SettingsController
from ._shutdown import ShutdownController
from ._system import LogsController, UpdateController

if TYPE_CHECKING:
    from gui import BotGUI

__all__ = [
    # 唯一打包函数
    "build_controllers",
    # 类型提示
    "BaseController",
    "SettingsController",
    "ShutdownController",
]

# 内部收集所有 Controller 类，便于统一遍历
_ALL_CONTROLLER_CLASSES = (
    DashboardController,
    LogsController,
    ProxyController,
    SettingsController,
    ShutdownController,
    UpdateController,
)


def build_controllers(
    gui_ref: "BotGUI",
) -> tuple[list[tuple[str, Callable]], list[BaseController]]:
    """实例化并打包控制器"""
    controllers = []
    instances = []
    for cls in _ALL_CONTROLLER_CLASSES:
        # 注入 GUI 引用，实例化控制器
        instance = cls(gui_ref)

        # 提取契约并打包
        controllers.append((instance.btn_id, instance.execute))

        instances.append(instance)

    return controllers, instances
