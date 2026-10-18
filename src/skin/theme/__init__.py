# src/skin/theme/__init__.py
"""主题门面

- 汇总调色板、核心、弹窗与引导令牌并实例化
- 导出全局单例
"""

from ._buttons import ButtonStyle
from ._core import (
    BodyTheme,
    ButtonDangerTheme,
    ButtonTheme,
    FontTheme,
    GlobalTheme,
    ScrollbarTheme,
    ToolbarTheme,
    WindowTheme,
)
from ._dialogs import (
    ChangeDialogTheme,
    CheckDialogTheme,
    FiveStateDialogTheme,
    LinkDialogTheme,
    NoticeDialogTheme,
    ShutdownDialogTheme,
    WaitDialogTheme,
)
from ._guide import (
    FormTheme,
    GuideButtonTheme,
    LaunchTheme,
    PanelTheme,
    PickerTheme,
)
from ._palette import PALETTE
from ._settings import SettingsDialogTheme, SettingsListTheme

__all__ = [
    # 调色板
    "PALETTE",
    # 按钮样式名
    "ButtonStyle",
    # 核心令牌类型
    "WindowTheme",
    "FontTheme",
    "GlobalTheme",
    "BodyTheme",
    "ToolbarTheme",
    "ButtonTheme",
    "ButtonDangerTheme",
    "ScrollbarTheme",
    # 弹窗令牌类型
    "SettingsDialogTheme",
    "SettingsListTheme",
    "ShutdownDialogTheme",
    "ChangeDialogTheme",
    "CheckDialogTheme",
    "WaitDialogTheme",
    "NoticeDialogTheme",
    "FiveStateDialogTheme",
    "LinkDialogTheme",
    # 引导令牌类型
    "PickerTheme",
    "FormTheme",
    "PanelTheme",
    "GuideButtonTheme",
    "LaunchTheme",
    # 核心单例
    "WINDOW",
    "FONT",
    "GLOBAL",
    "BODY",
    "TOOLBAR",
    "BTN",
    "BTN_DANGER",
    "SCROLLBAR",
    # 弹窗单例
    "SETTINGS_DIALOG",
    "LIST_DIALOG",
    "SHUTDOWN_DIALOG",
    "CHANGE_DIALOG",
    "CHECK_DIALOG",
    "WAIT_DIALOG",
    "NOTICE_DIALOG",
    "LINK_DIALOG",
    # 引导单例
    "PICKER",
    "FORM",
    "PANEL",
    "GUIDE_BTN",
    "LAUNCH",
]

# 核心令牌
WINDOW = WindowTheme()
FONT = FontTheme()
GLOBAL = GlobalTheme()
BODY = BodyTheme()
TOOLBAR = ToolbarTheme()
BTN = ButtonTheme()
BTN_DANGER = ButtonDangerTheme()
SCROLLBAR = ScrollbarTheme()

# 弹窗令牌
SETTINGS_DIALOG = SettingsDialogTheme()
LIST_DIALOG = SettingsListTheme()
SHUTDOWN_DIALOG = ShutdownDialogTheme()
CHANGE_DIALOG = ChangeDialogTheme()
CHECK_DIALOG = CheckDialogTheme()
WAIT_DIALOG = WaitDialogTheme()
NOTICE_DIALOG = NoticeDialogTheme()
LINK_DIALOG = LinkDialogTheme()

# 引导令牌
PICKER = PickerTheme()
FORM = FormTheme()
PANEL = PanelTheme()
GUIDE_BTN = GuideButtonTheme()
LAUNCH = LaunchTheme()
