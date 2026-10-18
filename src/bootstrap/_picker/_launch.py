# src/bootstrap/_picker/_launch.py
"""启动提示卡

- 选窗收场到主窗就绪之间给出可见的等待界面
- 启动导入分步泵事件，卡片靠正计时与重绘应答活着
- 主程序导入须留在主线程跑，界面组件在导入期即建 QObject
"""

import time

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
)

from skin.messages import PickerMessage
from skin.qss import build_bootstrap_qss
from skin.theme import LAUNCH
from widgets import Ticker, ensure_app

from ._store import remark_of

# 正计时刷新间隔，1 秒一格
_TICK_MS = 1000


class _LaunchWaitDialog(QDialog):
    """无边框提示卡，图标加两行文案带正计时

    - 分步泵事件让秒表逐秒刷新，界面全程有应答
    """

    def __init__(self, code: str) -> None:
        super().__init__()
        remark = remark_of(code)
        label = f"{remark}（{code}）" if remark else code
        self.setWindowTitle(PickerMessage.TITLE)
        self.setStyleSheet(build_bootstrap_qss())
        self.resize(LAUNCH.width, LAUNCH.height)

        # 无标题栏、置顶、跳过任务栏：没有可标"未响应"的载体
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )

        # 启动装载期半初始化界面收不到点击，直点一律放行到下层
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        row = QHBoxLayout(self)
        row.setSpacing(LAUNCH.gap)

        icon = QLabel()
        icon.setPixmap(ensure_app().windowIcon().pixmap(LAUNCH.icon_size))
        row.addWidget(icon)

        column = QVBoxLayout()
        column.setSpacing(LAUNCH.text_gap)
        text = QLabel(PickerMessage.LAUNCHING.format(label=label))
        text.setObjectName("launch_text")
        self._start = time.monotonic()
        self._note = QLabel()
        self._note.setObjectName("launch_note")
        self._tick()
        column.addWidget(text)
        column.addWidget(self._note)
        row.addLayout(column, 1)

        self._timer = Ticker(self, _TICK_MS, self._tick)
        self._timer.start()

        self._center_on_screen()

    def _tick(self) -> None:
        """副注行刷成正计时，泵到即跳秒"""
        sec = int(time.monotonic() - self._start)
        self._note.setText(PickerMessage.LAUNCHING_ELAPSED.format(sec=sec))

    def _center_on_screen(self) -> None:
        """屏幕正中落位，无边框窗不会自动居中"""
        area = ensure_app().primaryScreen().availableGeometry()
        self.move(
            area.x() + (area.width() - self.width()) // 2,
            area.y() + (area.height() - self.height()) // 2,
        )

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        """收起卡片即停表"""
        self._timer.stop()
        super().closeEvent(event)


def show_launch_wait(code: str) -> QDialog:
    """弹出启动提示卡并交回句柄

    - 调用方主窗就绪后对句柄 close 收起
    - 两轮 processEvents 分别兑现建窗与首帧合成，此后靠分步泵保持应答
    """
    app = ensure_app()
    dialog = _LaunchWaitDialog(code)
    dialog.show()
    dialog.raise_()
    dialog.activateWindow()
    app.processEvents()
    app.processEvents()
    return dialog
