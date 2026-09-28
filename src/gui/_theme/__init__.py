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
    NoticeDialogConfig,
    SettingsDialogConfig,
    SettingsListConfig,
    ShutdownDialogConfig,
    WaitDialogConfig,
)
from ._dialogs import FiveStateDialogConfig as FiveStateDialogConfig

# ==================== 实例化配置 ====================

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
