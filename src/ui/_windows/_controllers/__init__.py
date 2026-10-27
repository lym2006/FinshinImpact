# src/ui/_windows/_controllers/__init__.py
"""控制器门面

- 提供自动实例化与契约打包
"""

from collections.abc import Callable
from typing import TYPE_CHECKING

from ._base import BaseController
from ._dashboard import DashboardController
from ._diagnose import DiagnoseController, DiagnoseFlow
from ._release_notes import ReleaseNotesController
from ._settings import SettingsController
from ._shutdown import ShutdownController
from ._system import LogsController
from ._version import VersionController

if TYPE_CHECKING:
    from .._main_window import BotGUI


__all__ = [
    # 唯一打包函数
    "build_controllers",
    # 类型提示
    "BaseController",
    "DiagnoseFlow",
    "SettingsController",
    "ShutdownController",
]

# 只收 GUI 引用的控制器类，统一遍历实例化
_CONTROLLER_CLASSES = (
    DashboardController,
    LogsController,
    SettingsController,
    ShutdownController,
    VersionController,
    ReleaseNotesController,
)


def build_controllers(
    gui_ref: "BotGUI", diagnose_flow: DiagnoseFlow
) -> tuple[list[tuple[str, Callable]], list[BaseController]]:
    """实例化并打包控制器

    - 诊断控制器另收探测流程，不进统一遍历
    """
    # 诊断轮要跑平台探测，流程由上层交进来，视图层不直连适配层
    instances: list[BaseController] = [DiagnoseController(gui_ref, flow=diagnose_flow)]
    instances.extend(cls(gui_ref) for cls in _CONTROLLER_CLASSES)

    # 提取契约并打包
    controllers = [(instance.btn_id, instance.execute) for instance in instances]

    return controllers, instances
