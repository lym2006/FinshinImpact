# src/gui/dialogs/__init__.py
"""弹窗门面

- 提供全部弹窗组件导出
"""

from ._check import (
    CheckDialog,
    Round,
    current_check_window,
    open_check_window,
)
from ._notice import NoticeDialog
from ._settings import (
    ChangeConfirmDialog,
    ConfigMode,
    SettingsDialog,
)
from ._shutdown import ShutdownDialog
from ._wait import WaitDialog

__all__ = [
    # 配置修改
    "ChangeConfirmDialog",
    "ConfigMode",
    "SettingsDialog",
    # 关闭事件
    "ShutdownDialog",
    # 通用通知
    "NoticeDialog",
    # 检查进度（单实例）
    "CheckDialog",
    "Round",
    "current_check_window",
    "open_check_window",
    # 忙碌等待
    "WaitDialog",
]
