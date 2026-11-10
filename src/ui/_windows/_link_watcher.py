# src/ui/_windows/_link_watcher.py
"""链路断连计时观察

- 逐秒轮询链路快照，弹收断连计时弹窗
"""

from typing import TYPE_CHECKING

from PySide6.QtCore import QObject

from skin.messages import EngineMessage
from utils import get_logger
from utils.network import LinkStatus, link_report

from .._dialogs import LinkDialog, SettingsDialog, current_check_window
from .._lifecycle import Ticker

# 计时弹窗节奏
_POLL_MS = 1000  # 1 秒查一次链路快照

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget

_logger = get_logger("GUI.Link")


class LinkWatcher(QObject):
    """断连计时弹窗轮询器

    - 断连即弹，恢复即收
    - 叉号只压本次断连，静默压本次运行
    - 配置面板或检查进度窗在途时只记日志不弹窗，两者都收掉仍断连再补弹
    """

    def __init__(self, parent: "QWidget") -> None:
        super().__init__(parent)
        self._host = parent
        self._ticker: Ticker | None = None
        self._dialog: LinkDialog | None = None
        self._dismissed = False
        self._muted = False

        # 同一个原因只报一次，逐秒轮询不把面板刷满
        self._blocked_logged = ""

    def start(self) -> None:
        """启动逐秒轮询"""
        self._ticker = Ticker(self, _POLL_MS, self.poll)
        self._ticker.start()

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
        blocked = self._block_reason()
        if blocked:
            if blocked != self._blocked_logged:
                _logger.debug(f"断连计时窗未弹：{blocked}")
                self._blocked_logged = blocked
            return
        self._blocked_logged = ""
        self._show(status)

    def _block_reason(self) -> str:
        """当前压住弹窗的原因，没压住交空串"""
        if self._muted:
            return EngineMessage.BLOCK_MUTED
        if self._dismissed:
            return EngineMessage.BLOCK_DISMISSED
        if self._is_round_open():
            return EngineMessage.BLOCK_ROUND_OPEN
        return ""

    def _is_round_open(self) -> bool:
        """配置面板或检查进度窗当前是否开着"""
        panel = any(
            dialog.isVisible() for dialog in self._host.findChildren(SettingsDialog)
        )
        window = current_check_window()
        return panel or (window is not None and window.isVisible())

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
        """收起本次断连弹窗，再断连再弹"""
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
