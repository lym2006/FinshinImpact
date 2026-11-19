"""QApplication 取用处

- 建实例时挂图标
- 单轮事件泵供导入期垫住界面重绘
"""

import sys
from typing import cast

from PySide6.QtCore import QCoreApplication, QEventLoop
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
    """
    instance = QApplication.instance()
    if instance:
        return cast(QApplication, instance)
    app = QApplication(sys.argv)
    _apply_icon(app)
    return app


def pump_events() -> None:
    """泵一轮事件让已建界面应答重绘

    - 泵事件时排除用户输入
    """
    QCoreApplication.processEvents(QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents)
