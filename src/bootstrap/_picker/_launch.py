# src/bootstrap/_picker/_launch.py
"""启动提示卡

- 选窗收场到主窗就绪之间给出可见的等待界面
- 无边框窗不受系统"未响应"标题栏与白屏刷新影响
- 主程序导入须留在主线程跑，界面组件在导入期即建 QObject
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
)

from app_icon import ensure_app
from messages import PickerMessage

from .._qss import build_bootstrap_qss
from .._theme import LAUNCH
from ._store import remark_of


class _LaunchWaitDialog(QDialog):
    """无边框提示卡，图标加两行文案"""

    def __init__(self, code: str) -> None:
        super().__init__()
        remark = remark_of(code)
        label = f"{remark}（{code}）" if remark else code
        self.setWindowTitle(PickerMessage.TITLE)
        self.setStyleSheet(build_bootstrap_qss())
        self.resize(LAUNCH.width, LAUNCH.height)

        # 无标题栏、置顶、跳过任务栏：定格画面没有可标"未响应"的载体
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )

        row = QHBoxLayout(self)
        row.setSpacing(LAUNCH.gap)

        icon = QLabel()
        icon.setPixmap(ensure_app().windowIcon().pixmap(LAUNCH.icon_size))
        row.addWidget(icon)

        column = QVBoxLayout()
        column.setSpacing(LAUNCH.text_gap)
        text = QLabel(PickerMessage.LAUNCHING.format(label=label))
        text.setObjectName("launch_text")
        note = QLabel(PickerMessage.LAUNCHING_NOTE)
        note.setObjectName("launch_note")
        column.addWidget(text)
        column.addWidget(note)
        row.addLayout(column, 1)

        self._center_on_screen()

    def _center_on_screen(self) -> None:
        """屏幕正中落位，无边框窗不会自动居中"""
        area = ensure_app().primaryScreen().availableGeometry()
        self.move(
            area.x() + (area.width() - self.width()) // 2,
            area.y() + (area.height() - self.height()) // 2,
        )


def show_launch_wait(code: str) -> QDialog:
    """弹出启动提示卡并交回句柄

    - 调用方主窗就绪后对句柄 close 收起
    - 两轮 processEvents 分别兑现建窗与首帧合成，主线程随后定格在该画面
    """
    app = ensure_app()
    dialog = _LaunchWaitDialog(code)
    dialog.show()
    dialog.raise_()
    dialog.activateWindow()
    app.processEvents()
    app.processEvents()
    return dialog
