# src/gui/icon.py
"""应用图标

- 挂接主窗口图标与 Windows 任务栏身份
- 图标文件与启动器 exe 同源，缺文件时静默降级
"""

import ctypes
import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

# assets/app.ico 随 _COPY_DIRS 进发布包，开发态与发布态目录层级一致
_ICON_PATH = Path(__file__).resolve().parents[2] / "assets" / "app.ico"
_APP_ID = "TelegramBot.GUI"  # 任务栏归属身份，缺省则图标随宿主 pythonw.exe


def _set_taskbar_identity() -> None:
    """任务栏身份声明

    Windows 任务栏图标跟随进程身份而非窗口图标，不显式声明就沿用解释器的 Python 图标。
    """
    if sys.platform == "win32":
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(_APP_ID)


def apply_icon(app: QApplication) -> None:
    """设置应用图标

    先验图标再声明身份：图标缺失若仍声明，Explorer 会把 Python 图标绑进该身份的缓存。
    """
    if not _ICON_PATH.is_file():
        return
    _set_taskbar_identity()
    app.setWindowIcon(QIcon(str(_ICON_PATH)))
