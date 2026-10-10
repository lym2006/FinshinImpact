# src/gui/_theme/__init__.py
"""主题门面

- 汇总核心与弹窗令牌并实例化
- 导出全局单例
"""

from ._core import (
    BodyConfig,
    ButtonConfig,
    ButtonDangerConfig,
    FontConfig,
    GlobalConfig,
    ScrollbarConfig,
    ToolbarConfig,
    WindowConfig,
)
from ._dialogs import (
    ChangeDialogConfig,
    CheckDialogConfig,
    FiveStateDialogConfig,
    NoticeDialogConfig,
    SettingsDialogConfig,
    SettingsListConfig,
    ShutdownDialogConfig,
    WaitDialogConfig,
)

__all__ = [
    # 核心令牌类型
    "WindowConfig",
    "FontConfig",
    "GlobalConfig",
    "BodyConfig",
    "ToolbarConfig",
    "ButtonConfig",
    "ButtonDangerConfig",
    "ScrollbarConfig",
    # 弹窗令牌类型
    "SettingsDialogConfig",
    "SettingsListConfig",
    "ShutdownDialogConfig",
    "ChangeDialogConfig",
    "CheckDialogConfig",
    "WaitDialogConfig",
    "NoticeDialogConfig",
    "FiveStateDialogConfig",
    # 实例单例
    "WINDOW",
    "FONT",
    "GLOBAL",
    "BODY",
    "TOOLBAR",
    "BTN",
    "BTN_DANGER",
    "SCROLLBAR",
    "SETTINGS_DIALOG",
    "LIST_DIALOG",
    "SHUTDOWN_DIALOG",
    "CHANGE_DIALOG",
    "CHECK_DIALOG",
    "WAIT_DIALOG",
    "NOTICE_DIALOG",
]

# 在模块级别实例化，供外部导入使用
WINDOW = WindowConfig()
FONT = FontConfig()
GLOBAL = GlobalConfig()
BODY = BodyConfig()
TOOLBAR = ToolbarConfig()
BTN = ButtonConfig()
BTN_DANGER = ButtonDangerConfig()
SCROLLBAR = ScrollbarConfig()
SETTINGS_DIALOG = SettingsDialogConfig()
LIST_DIALOG = SettingsListConfig()
SHUTDOWN_DIALOG = ShutdownDialogConfig()
CHANGE_DIALOG = ChangeDialogConfig()
CHECK_DIALOG = CheckDialogConfig()
WAIT_DIALOG = WaitDialogConfig()
NOTICE_DIALOG = NoticeDialogConfig()
