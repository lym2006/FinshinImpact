# src/gui/_theme/__init__.py
"""主题门面

- 汇总核心与弹窗令牌并实例化
- 导出全局单例与按钮清单
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
    FatalDialogConfig,
    HintDialogConfig,
    ProxyDialogConfig,
    SettingsDialogConfig,
    SettingsListConfig,
    ShutdownDialogConfig,
    WaitDialogConfig,
)

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
FATAL_DIALOG = FatalDialogConfig()
CHANGE_DIALOG = ChangeDialogConfig()
PROXY_DIALOG = ProxyDialogConfig()
WAIT_DIALOG = WaitDialogConfig()
HINT_DIALOG = HintDialogConfig()

# ==================== 按钮列表 ====================

TOOLBAR_BUTTONS = [
    ("修改配置", "settings"),
    ("网络诊断", "proxy"),
    ("查看日志", "log"),
    ("检查更新", "update"),
    ("清空仪表盘", "clear"),
    ("关闭机器人", "shutdown"),
]
