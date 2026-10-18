# src/ui/_lifecycle/_app.py
"""应用实例工厂

- 全进程 QApplication 唯一出生口，建实例即挂图标
"""

import sys
from typing import cast

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from system.app_identity import APP_ICON_PATH


def _apply_icon(app: QApplication) -> None:
    """设置应用图标"""
    if APP_ICON_PATH.is_file():
        app.setWindowIcon(QIcon(str(APP_ICON_PATH)))


def ensure_app() -> QApplication:
    """取得应用实例

    - 不存在则新建并挂图标，全进程图标只在出生这一刻设置
    - instance 静态类型是基类，收窄为 QApplication
    """
    instance = QApplication.instance()
    if instance:
        return cast(QApplication, instance)
    app = QApplication(sys.argv)
    _apply_icon(app)
    return app
