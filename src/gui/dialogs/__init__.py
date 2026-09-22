# src/gui/dialogs/__init__.py
"""弹窗门面

- 提供全部弹窗组件导出
"""

from ._fatal import FatalDialog
from ._hint import HintDialog
from ._proxy import ProxyDialog
from ._settings import (
    ChangeConfirmDialog,
    ConfigMode,
    NotChangedDialog,
    SettingsDialog,
)
from ._shutdown import ShutdownDialog
from ._wait import WaitDialog

__all__ = [
    # 配置修改
    "ChangeConfirmDialog",
    "ConfigMode",
    "NotChangedDialog",
    "SettingsDialog",
    # 关闭事件
    "ShutdownDialog",
    # 致命错误
    "FatalDialog",
    # 通用提示
    "HintDialog",
    # 网络诊断
    "ProxyDialog",
    # 忙碌等待
    "WaitDialog",
]
