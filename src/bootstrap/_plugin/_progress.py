# src/bootstrap/_plugin/_progress.py
"""引导期进度窗

- 后台线程执行装卸任务，子进程输出逐行滚动展示
- 任务未完禁关，做完才能继续启动
"""

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QCloseEvent, QFont
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from app_icon import ensure_app
from messages import PluginMessage

from .._qss import build_bootstrap_qss
from ._support import log_ops

# 日志字体族与字号
_LOG_FONT_FAMILY = "Consolas"
_LOG_FONT_SIZE = 9

# 进度窗宽与日志区高（像素）
_WINDOW_WIDTH = 640
_LOG_HEIGHT = 320

# 逐行回调签名
_LineFn = Callable[[str], None]

# 任务函数签名：收逐行回调、回失败项列表
_TaskFn = Callable[[_LineFn], list[Any]]


class _Task(QThread):
    """装卸任务工作线程"""

    line_written = Signal(str)
    result_ready = Signal(list)

    def __init__(self, fn: _TaskFn, title: str) -> None:
        super().__init__()
        self._fn = fn
        self.title = title
        self.lines: list[str] = []
        self.failed: list[Any] = []
        self.done = False

    def run(self) -> None:
        """执行任务并把失败项交回主线程"""

        def on_line(text: str) -> None:
            # 先落缓冲再发信号，补打快照与实时尾随共用一份数据
            self.lines.append(text)
            self.line_written.emit(text)

        try:
            self.failed = list(self._fn(on_line))
        except Exception as exc:
            log_ops([f"[task:{self.title}] {type(exc).__name__}: {exc}"])
            self.failed = [PluginMessage.TASK_FAIL]
        self.done = True
        self.result_ready.emit(self.failed)


class _ProgressDialog(QDialog):
    """模态进度窗，任务未完禁关"""

    def __init__(self, title: str, fn: _TaskFn) -> None:
        """起窗即启动任务线程"""
        super().__init__()
        self._seen = 0
        self._task = _Task(fn, title)
        self.setWindowTitle(title)
        self.setStyleSheet(build_bootstrap_qss())
        self.resize(_WINDOW_WIDTH, _LOG_HEIGHT)

        layout = QVBoxLayout(self)
        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setObjectName("progress_log")
        self._log.setFont(QFont(_LOG_FONT_FAMILY, _LOG_FONT_SIZE))
        layout.addWidget(self._log)

        self._button = QPushButton(PluginMessage.BTN_DONE)
        self._button.setEnabled(False)
        self._button.clicked.connect(self.accept)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(self._button)
        layout.addLayout(row)

        self._task.line_written.connect(self._drain)
        self._task.result_ready.connect(self._finish)
        self._task.start()
        self._drain()
        if self._task.done:
            self._finish()

    def failed_items(self) -> list[Any]:
        """取任务失败项"""
        return list(self._task.failed)

    def _drain(self) -> None:
        # 索引去重：缓冲快照与信号尾随可能重叠打行
        for line in self._task.lines[self._seen :]:
            self._log.appendPlainText(line)
        self._seen = len(self._task.lines)

    def _finish(self) -> None:
        self._button.setEnabled(True)

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        """任务未完禁关窗"""
        if not self._task.done:
            event.ignore()
            return
        super().closeEvent(event)

    def reject(self) -> None:
        """Esc 等隐式关闭同样禁关"""
        if not self._task.done:
            return
        super().reject()


def run_with_progress(title: str, fn: _TaskFn) -> list[Any]:
    """模态起进度窗跑任务，返回失败项列表"""
    ensure_app()
    dialog = _ProgressDialog(title, fn)
    dialog.exec()
    return dialog.failed_items()
