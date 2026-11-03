# src/ui/_dialogs/__init__.py
"""弹窗子包门面

- 代发基类、提示、等待、关闭确认与配置、检查、断连、版本变化、人设对账各类业务弹窗
- 代发自家两窗之间的常驻浮顶件
"""

from ._base import BaseDialog
from ._check import (
    CheckDialog,
    Round,
    current_check_window,
    open_check_window,
)
from ._follow import follow_above
from ._link import LinkDialog
from ._notice import NoticeDialog
from ._persona import PersonaResolveDialog, PersonaSyncDialog
from ._release_notes import ReleaseNotesDialog
from ._restart import close_restart_wait, finish_restart_wait, show_restart_wait
from ._settings import ChangeConfirmDialog, ConfigMode, SettingsDialog
from ._shutdown import ShutdownDialog
from ._wait import WaitDialog

__all__ = [
    # 弹窗基类
    "BaseDialog",
    # 通用弹窗
    "NoticeDialog",
    "PersonaSyncDialog",
    "ReleaseNotesDialog",
    "WaitDialog",
    "ShutdownDialog",
    # 业务弹窗
    "SettingsDialog",
    "ConfigMode",
    "ChangeConfirmDialog",
    "PersonaResolveDialog",
    "CheckDialog",
    "Round",
    "current_check_window",
    "follow_above",
    "open_check_window",
    "close_restart_wait",
    "finish_restart_wait",
    "show_restart_wait",
    "LinkDialog",
]
