# src/ui/_dialogs/__init__.py
"""弹窗子包门面

- 代发基类、提示、等待、关闭确认与配置、检查、断连各类业务弹窗
"""

from ._base import BaseDialog
from ._check import (
    CheckDialog,
    Round,
    current_check_window,
    open_check_window,
)
from ._link import LinkDialog
from ._notice import NoticeDialog
from ._settings import (
    ChangeConfirmDialog,
    ConfigMode,
    SettingsDialog,
)
from ._shutdown import ShutdownDialog
from ._wait import WaitDialog

__all__ = [
    # 弹窗基类
    "BaseDialog",
    # 通用弹窗
    "NoticeDialog",
    "WaitDialog",
    "ShutdownDialog",
    # 业务弹窗
    "SettingsDialog",
    "ConfigMode",
    "ChangeConfirmDialog",
    "CheckDialog",
    "Round",
    "current_check_window",
    "open_check_window",
    "LinkDialog",
]
