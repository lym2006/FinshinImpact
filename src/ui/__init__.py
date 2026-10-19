# src/ui/__init__.py
"""视图层门面

- 按属性惰性解析，取用哪个符号才 import 哪个子包
- 代发控件构造、生命周期件、信号桥、各类弹窗、引导期窗体与主窗装配
"""

import importlib
from typing import TYPE_CHECKING

_SYMBOL_MODULES = {
    "gui_bridge": "._bridge",
    "BaseDialog": "._dialogs",
    "NoticeDialog": "._dialogs",
    "ShutdownDialog": "._dialogs",
    "CheckDialog": "._dialogs",
    "Round": "._dialogs",
    "current_check_window": "._dialogs",
    "open_check_window": "._dialogs",
    "LinkDialog": "._dialogs",
    "ChangeConfirmDialog": "._dialogs",
    "ConfigMode": "._dialogs",
    "SettingsDialog": "._dialogs",
    "WaitDialog": "._dialogs",
    "pick_profile": "._guide",
    "show_launch_wait": "._guide",
    "show_popup": "._guide",
    "open_panel": "._guide",
    "MODE_AUTO": "._guide",
    "settle_runtime": "._guide",
    "ensure_app": "._lifecycle",
    "pump_events": "._lifecycle",
    "Ticker": "._lifecycle",
    "TickedCheckBox": "._primitives",
    "make_button": "._primitives",
    "make_combo": "._primitives",
    "ThemedList": "._primitives",
    "create_gui": "._windows",
    "BotGUI": "._windows",
    "LinkWatcher": "._windows",
    "build_controllers": "._windows",
    "BaseController": "._windows",
    "SettingsController": "._windows",
    "ShutdownController": "._windows",
}

__all__ = [
    # 信号桥
    "gui_bridge",
    # 应用实例与事件泵
    "ensure_app",
    "pump_events",
    # 弹窗基类
    "BaseDialog",
    # 控件
    "TickedCheckBox",
    "ThemedList",
    # 按钮
    "make_button",
    "make_combo",
    # 通用弹窗
    "NoticeDialog",
    "WaitDialog",
    "ShutdownDialog",
    # 业务弹窗
    "CheckDialog",
    "Round",
    "current_check_window",
    "open_check_window",
    "LinkDialog",
    "SettingsDialog",
    "ConfigMode",
    "ChangeConfirmDialog",
    # 计时泵
    "Ticker",
    # 引导期窗体
    "pick_profile",
    "show_launch_wait",
    "show_popup",
    "open_panel",
    "MODE_AUTO",
    "settle_runtime",
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

if TYPE_CHECKING:
    from ._bridge import gui_bridge
    from ._dialogs import (
        BaseDialog,
        ChangeConfirmDialog,
        CheckDialog,
        ConfigMode,
        LinkDialog,
        NoticeDialog,
        Round,
        SettingsDialog,
        ShutdownDialog,
        WaitDialog,
        current_check_window,
        open_check_window,
    )
    from ._guide import (
        MODE_AUTO,
        open_panel,
        pick_profile,
        settle_runtime,
        show_launch_wait,
        show_popup,
    )
    from ._lifecycle import Ticker, ensure_app, pump_events
    from ._primitives import (
        ThemedList,
        TickedCheckBox,
        make_button,
        make_combo,
    )
    from ._windows import (
        BaseController,
        BotGUI,
        LinkWatcher,
        SettingsController,
        ShutdownController,
        build_controllers,
        create_gui,
    )


def __getattr__(name: str) -> object:
    module_path = _SYMBOL_MODULES.get(name)
    if module_path is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(module_path, __name__)
    return getattr(module, name)
