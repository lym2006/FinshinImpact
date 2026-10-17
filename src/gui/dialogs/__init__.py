# src/gui/dialogs/__init__.py
"""弹窗门面

- 提供业务弹窗组件导出
"""

from ._check import (
    CheckDialog,
    Round,
    current_check_window,
    open_check_window,
)
from ._link import LinkDialog
from ._settings import (
    ChangeConfirmDialog,
    ConfigMode,
    SettingsDialog,
)

__all__ = [
    # 配置修改
    "ChangeConfirmDialog",
    "ConfigMode",
    "SettingsDialog",
    # 断连计时
    "LinkDialog",
    # 检查进度（单实例）
    "CheckDialog",
    "Round",
    "current_check_window",
    "open_check_window",
]
