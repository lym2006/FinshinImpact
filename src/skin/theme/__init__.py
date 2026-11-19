"""主题门面

- 汇总调色板、核心、弹窗与引导令牌并实例化
- 导出全局单例
"""

from ._buttons import ButtonSize, ButtonStyle, button_object_name
from ._dialogs import (
    ChangeDialogTheme,
    CheckDialogTheme,
    FiveStateDialogTheme,
    LinkDialogTheme,
    NoticeDialogTheme,
    PlatformDialogTheme,
    ReleaseNotesDialogTheme,
    ShutdownDialogTheme,
    WaitDialogTheme,
)
from ._global import (
    BodyTheme,
    FontTheme,
    GlobalTheme,
    ScrollbarTheme,
    ToolbarTheme,
    WindowTheme,
)
from ._guide import (
    FormTheme,
    GuideFieldTheme,
    LaunchTheme,
    PanelTheme,
    PickerTheme,
)
from ._names import ObjectName
from ._palette import PALETTE
from ._settings import SettingsDialogTheme, SettingsListTheme

__all__ = [
    # 调色板
    "PALETTE",
    # 按钮样式名
    "ButtonStyle",
    "ButtonSize",
    "button_object_name",
    # 控件对象名
    "ObjectName",
    # 核心令牌类型
    "WindowTheme",
    "FontTheme",
    "GlobalTheme",
    "BodyTheme",
    "ToolbarTheme",
    "ScrollbarTheme",
    # 弹窗令牌类型
    "SettingsDialogTheme",
    "SettingsListTheme",
    "ShutdownDialogTheme",
    "ChangeDialogTheme",
    "CheckDialogTheme",
    "WaitDialogTheme",
    "NoticeDialogTheme",
    "PlatformDialogTheme",
    "ReleaseNotesDialogTheme",
    "FiveStateDialogTheme",
    "LinkDialogTheme",
    # 引导令牌类型
    "PickerTheme",
    "FormTheme",
    "PanelTheme",
    "GuideFieldTheme",
    "LaunchTheme",
    # 核心单例
    "WINDOW",
    "FONT",
    "GLOBAL",
    "BODY",
    "TOOLBAR",
    "SCROLLBAR",
    # 弹窗单例
    "SETTINGS_DIALOG",
    "LIST_DIALOG",
    "SHUTDOWN_DIALOG",
    "CHANGE_DIALOG",
    "CHECK_DIALOG",
    "WAIT_DIALOG",
    "NOTICE_DIALOG",
    "PLATFORM_DIALOG",
    "RELEASE_NOTES_DIALOG",
    "LINK_DIALOG",
    # 引导单例
    "PICKER",
    "FORM",
    "PANEL",
    "GUIDE_FIELD",
    "LAUNCH",
]

# 核心令牌
WINDOW = WindowTheme()
FONT = FontTheme()
GLOBAL = GlobalTheme()
BODY = BodyTheme()
TOOLBAR = ToolbarTheme()
SCROLLBAR = ScrollbarTheme()

# 弹窗令牌
SETTINGS_DIALOG = SettingsDialogTheme()
LIST_DIALOG = SettingsListTheme()
SHUTDOWN_DIALOG = ShutdownDialogTheme()
CHANGE_DIALOG = ChangeDialogTheme()
CHECK_DIALOG = CheckDialogTheme()
WAIT_DIALOG = WaitDialogTheme()
NOTICE_DIALOG = NoticeDialogTheme()
PLATFORM_DIALOG = PlatformDialogTheme()
RELEASE_NOTES_DIALOG = ReleaseNotesDialogTheme()
LINK_DIALOG = LinkDialogTheme()

# 引导令牌
PICKER = PickerTheme()
FORM = FormTheme()
PANEL = PanelTheme()
GUIDE_FIELD = GuideFieldTheme()
LAUNCH = LaunchTheme()
