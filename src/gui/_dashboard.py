# src/gui/_dashboard.py
"""仪表盘（内部实现）

- 定义日志面板渲染组件
- 定义日志重定向 Handler
"""

import logging
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtGui import QFont, QFontDatabase, QTextCursor
from PySide6.QtWidgets import QTextEdit

from exceptions import (
    DashboardWriteError,
    FontError,
    FontFamilyError,
    FontLoadError,
    FontMissingError,
    FontRegisterError,
)

from ._theme import FontConfig

FontType = tuple[QFont, str, str]

# ==================== 线程安全信号桥 ====================


class _LogSignal(QObject):
    """内部跨线程信号桥接器"""

    log_received = Signal(str)


# ==================== 日志处理器 ====================


class TextHandler(logging.Handler):
    """仪表盘日志重定向 Handler"""

    def __init__(self, widget: "DashboardWidget", formatter: logging.Formatter) -> None:
        super().__init__()
        self._widget = widget

        # 创建信号桥接器并连接到 UI 更新方法
        self._signal = _LogSignal()
        self._signal.log_received.connect(self._append_text)

        # 设置默认日志格式
        self.setFormatter(formatter)

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


# ==================== 仪表盘组件 ====================


class DashboardWidget(QTextEdit):
    """仪表盘纯展示组件"""

    def __init__(self, fonts: FontConfig, parent=None) -> None:
        super().__init__(parent)

        # 基础属性设置
        self.setReadOnly(True)
        self.setObjectName("dashboard")

        # 加载字体
        font = self._load_font(fonts.font_path, fonts.font_size)
        _ = self.setFont(font)

        # 加载 Emoji 字体（静默失败，内部兜底）
        self._load_font(fonts.emoji_path, fonts.font_size, silent=True)

    def _load_font(
        self, font_path: Path, font_size: int, silent: bool = False
    ) -> QFont:
        """加载自定义字体"""

        def _handle_failure(exc: Exception) -> QFont:
            if silent:
                return self._get_fallback_font(font_size)
            raise exc

        if not font_path.exists():
            # 字体文件不存在
            return _handle_failure(FontMissingError(font_path))

        try:
            font_id = QFontDatabase.addApplicationFont(str(font_path))
            if font_id == -1:
                # Qt 无法加载字体文件
                return _handle_failure(FontLoadError(font_path))

            families = QFontDatabase.applicationFontFamilies(font_id)
            if not families:
                # 字体文件无法获取家族
                return _handle_failure(FontFamilyError(font_path))

            return QFont(families[0], font_size)

        except FontError:
            raise
        except Exception as e:
            # 注册字体失败
            err = FontRegisterError(font_path)
            err.__cause__ = e
            return _handle_failure(err)

    @staticmethod
    def _get_fallback_font(font_size: int) -> QFont:
        """获取系统默认兜底字体"""
        fallback = QFont("Consolas", font_size)
        fallback.setStyleHint(QFont.StyleHint.Monospace)
        return fallback
