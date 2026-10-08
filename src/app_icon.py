# src/app_icon.py
"""应用图标

- 挂接应用图标与 Windows 任务栏身份
- 身份锚定启动器 exe，图标文件缺失只降级窗口图标
- 引导层建应用实例即挂图标，选窗与主窗共用同一身份
"""

import ctypes
import os
import sys
from pathlib import Path
from typing import cast

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from profile_env import ASSETS_DIR

# assets/app.ico 随 _COPY_DIRS 进发布包，开发态与发布态目录层级一致
_ICON_PATH = ASSETS_DIR / "app.ico"

# 与启动器 _AUMID_ANCHOR_VAR 是同一份约定，两处改名必须同步
_AUMID_ANCHOR_VAR = "FINSHINIMPACT_EXE_PATH"

# 导入即声明身份：Qt 首建窗口那一刻就向窗口写身份，晚设不影响已建按钮
_anchor = os.environ.get(_AUMID_ANCHOR_VAR, "")
if sys.platform == "win32" and _anchor and Path(_anchor).is_file():
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(_anchor)


def apply_icon(app: QApplication) -> None:
    """设置应用图标"""
    if _ICON_PATH.is_file():
        app.setWindowIcon(QIcon(str(_ICON_PATH)))


def ensure_app() -> QApplication:
    """取得应用实例

    - 不存在则新建并挂图标，全进程图标只在出生这一刻设置
    - instance 静态类型是基类，收窄为 QApplication
    """
    instance = QApplication.instance()
    if instance:
        return cast(QApplication, instance)
    app = QApplication(sys.argv)
    apply_icon(app)
    return app
