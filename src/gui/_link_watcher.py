# src/gui/_link_watcher.py
"""链路断连计时观察

- 逐秒轮询链路快照，弹收断连计时弹窗
"""

from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QTimer

from utils.network import LinkStatus, link_report

from .dialogs import LinkDialog

# 计时弹窗节奏
_POLL_MS = 1000  # 1 秒查一次链路快照

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget


class LinkWatcher(QObject):
    """断连计时弹窗轮询器

    - 断连即弹，恢复即收
    - 叉号只压本轮断连，静默压本次运行
    """

    def __init__(self, parent: "QWidget") -> None:
        super().__init__(parent)
        self._host = parent
        self._timer: QTimer | None = None
        self._dialog: LinkDialog | None = None
        self._dismissed = False
        self._muted = False

    def start(self) -> None:
        """启动逐秒轮询"""
        self._timer = timer = QTimer(self)
        timer.setInterval(_POLL_MS)
        timer.timeout.connect(self.poll)
        timer.start()

    def poll(self) -> None:
        """按链路快照弹收计时弹窗"""
        status = link_report.snapshot()
        if not status.down:
            self._dismissed = False
            self._drop()
            return

        if self._dialog is not None:
            self._dialog.refresh(status)
            return
        if self._muted or self._dismissed:
            return
        self._show(status)

    def _show(self, status: LinkStatus) -> None:
        """弹出计时窗并写入首帧"""
        dialog = LinkDialog(
            on_close=self._on_close,
            on_mute=self._on_mute,
            parent=self._host,
        )
        dialog.refresh(status)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        self._dialog = dialog

    def _on_close(self) -> None:
        """收起本轮，下次断连再弹"""
        self._dismissed = True
        self._dialog = None

    def _on_mute(self) -> None:
        """本次运行内保持静默"""
        self._muted = True
        self._on_close()

    def _drop(self) -> None:
        """恢复后收起计时窗"""
        if self._dialog is not None:
            self._dialog.hide()
        self._dialog = None
