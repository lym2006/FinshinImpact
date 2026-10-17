# src/system/app_identity.py
"""进程应用身份

- 任务栏身份锚定启动器 exe，导入即声明，晚设不影响已建窗口
- 图标文件路径供组装层挂窗口图标
"""

import ctypes
import os
import sys
from pathlib import Path

from .profile_env import ASSETS_DIR

# assets/app.ico 随 _COPY_DIRS 进发布包，开发态与发布态目录层级一致
APP_ICON_PATH = ASSETS_DIR / "app.ico"

# 与启动器 _AUMID_ANCHOR_VAR 是同一份约定，两处改名必须同步
_AUMID_ANCHOR_VAR = "FINSHINIMPACT_EXE_PATH"

# 导入即声明身份：Qt 首建窗口那一刻就向窗口写身份，晚设不影响已建按钮
_anchor = os.environ.get(_AUMID_ANCHOR_VAR, "")
if sys.platform == "win32" and _anchor and Path(_anchor).is_file():
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(_anchor)
