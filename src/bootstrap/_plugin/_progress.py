# src/bootstrap/_plugin/_progress.py
"""引导期进度窗

- 后台线程执行装卸任务，子进程输出逐行滚动展示
- 任务进行中窗口不可关闭，强关后任务继续后台运行，本轮按失败计
- 转后台的任务留在注册表，主窗就绪后由 rearm_detached 重新弹出展示
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

# 强关时返回的占位失败项，调用方按"未装齐"处理即可
_DETACHED_RESULT = ["<后台继续>"]

# 逐行回调签名
_LineFn = Callable[[str], None]

# 任务函数签名：收逐行回调、回失败项列表
_TaskFn = Callable[[_LineFn], list[Any]]

# 强关后仍在跑的任务，持引用防 QThread 提前析构并供续显
_DETACHED: set["_Task"] = set()

# 续显窗引用集，防无父级窗被提前回收
_VIEWS: set["_RearmView"] = set()


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
            # 先落缓冲再发信号，续显快照与实时尾随共用一份数据
            self.lines.append(text)
            self.line_written.emit(text)

        try:
            self.failed = list(self._fn(on_line))
        except Exception as exc:
            log_ops([f"[task:{self.title}] {type(exc).__name__}: {exc}"])
            self.failed = [PluginMessage.TASK_FAIL]
        self.done = True
        self.result_ready.emit(self.failed)


class _LogDialog(QDialog):
    """滚动日志窗体

    - 输出先读任务缓冲补历史，再随信号逐行刷新
    """

    def __init__(self, title: str) -> None:
        super().__init__()
        self._task: _Task | None = None
        self._seen = 0
        self.setWindowTitle(title)
        self.setStyleSheet(build_bootstrap_qss())
        self.resize(_WINDOW_WIDTH, _LOG_HEIGHT)

        layout = QVBoxLayout(self)
        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setObjectName("progress_log")
        self._log.setFont(QFont(_LOG_FONT_FAMILY, _LOG_FONT_SIZE))
        layout.addWidget(self._log)

        self._button = QPushButton(PluginMessage.BTN_ABORT)
        self._button.clicked.connect(self._on_button)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(self._button)
        layout.addLayout(row)

    def attach(self, task: _Task) -> None:
        """绑定任务，补打已缓冲输出并订阅后续行"""
        self._task = task
        task.line_written.connect(self._drain)
        task.result_ready.connect(self._finish)
        self._drain()
        if task.done:
            self._finish()

    def _drain(self) -> None:
        # 索引去重：attach 快照与信号尾随可能重叠打行
        if self._task is None:
            return
        for line in self._task.lines[self._seen :]:
            self._log.appendPlainText(line)
        self._seen = len(self._task.lines)

    def _finish(self) -> None:
        self._button.setText(PluginMessage.BTN_DONE)

    def _on_button(self) -> None:
        raise NotImplementedError


class _ProgressDialog(_LogDialog):
    """模态进度窗，任务未完禁关，强关后任务转后台"""

    def __init__(self, title: str, fn: _TaskFn) -> None:
        """起窗即启动后台任务"""
        super().__init__(title)
        self._detached = False
        self._task = _Task(fn, title)
        self.attach(self._task)
        self._task.start()

    def failed_items(self) -> list[Any]:
        """取任务失败项，强关一律按失败计"""
        if self._detached or self._task is None:
            return list(_DETACHED_RESULT)
        return list(self._task.failed)

    def _on_button(self) -> None:
        if self._task is not None and self._task.done:
            self.accept()
            return

        # 强关：任务继续跑完，引用交给模块注册表托管
        self._detached = True
        if self._task is not None:
            _DETACHED.add(self._task)
            self._task.finished.connect(self._release)
        self.accept()

    def _release(self) -> None:
        if self._task is not None:
            _DETACHED.discard(self._task)

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        """任务未完禁关窗"""
        if self._task is not None and not self._task.done and not self._detached:
            event.ignore()
            return
        super().closeEvent(event)

    def reject(self) -> None:
        """Esc 等隐式关闭同样受禁关约束"""
        if self._task is not None and not self._task.done and not self._detached:
            return
        super().reject()


class _RearmView(_LogDialog):
    """后台装卸任务展示窗，关闭不影响任务运行"""

    def __init__(self, task: _Task) -> None:
        super().__init__(f"{task.title}（后台进行中）")
        self._button.setText(PluginMessage.BTN_DONE)
        self.attach(task)

    def _on_button(self) -> None:
        _VIEWS.discard(self)
        self.accept()


def run_with_progress(title: str, fn: _TaskFn) -> list[Any]:
    """模态起进度窗跑任务，返回失败项列表"""
    ensure_app()
    dialog = _ProgressDialog(title, fn)
    dialog.exec()
    return dialog.failed_items()


def rearm_detached() -> None:
    """主窗就绪后把仍在后台运行的装卸任务重新弹出展示"""
    for task in list(_DETACHED):
        if task.done:
            _DETACHED.discard(task)
            continue
        view = _RearmView(task)
        _VIEWS.add(view)
        view.show()
