# src/gui/_dashboard.py
"""仪表盘

- 定义日志面板渲染组件
- 定义日志重定向 Handler
"""

import logging

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QTextEdit, QWidget

from exceptions import DashboardWriteError
from theme import load_font

from ._theme import FontConfig


class _LogSignal(QObject):
    """跨线程信号桥接器"""

    log_received = Signal(str)


class TextHandler(logging.Handler):
    """仪表盘日志重定向 Handler"""

    def __init__(self, widget: "DashboardWidget", formatter: logging.Formatter) -> None:
        super().__init__()
        self._widget = widget

        # 创建信号桥接器并连接到 UI 更新方法
        self._signal = _LogSignal()
        self._signal.log_received.connect(self._append_text)

        self.setFormatter(formatter)  # 设置默认日志格式

    def emit(self, record: logging.LogRecord) -> None:
        """接收并处理日志记录"""
        try:
            msg: str = self.format(record) + "\n"
            self._signal.log_received.emit(msg)

        except Exception:
            self.handleError(record)

    @Slot(str)
    def _append_text(self, msg: str) -> None:
        """将文本追加到仪表盘并自动滚动"""
        try:
            cursor = self._widget.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.insertText(msg)
            scrollbar = self._widget.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

        except Exception as e:
            # GUI 写入日志出错
            raise DashboardWriteError() from e


class DashboardWidget(QTextEdit):
    """仪表盘日志展示组件"""

    def __init__(self, fonts: FontConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.setReadOnly(True)  # 基础属性设置
        self.setObjectName("dashboard")

        # 加载字体
        font = load_font(fonts.font_path, fonts.font_size)
        _ = self.setFont(font)

        # 加载 Emoji 字体（静默失败，内部兜底）
        _ = load_font(fonts.emoji_path, fonts.font_size, silent=True)
