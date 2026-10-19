# src/gui/controllers/_proxy.py
"""网络诊断控制器（内部实现）

- 提供连通性自助排查入口
"""

from utils import config_manager

from ..dialogs import ProxyDialog
from ._base import BaseController


class ProxyController(BaseController):
    """网络诊断控制器"""

    LOGGER_NAME = "GUI.Proxy"
    BTN_KEY = "proxy"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # 非模态期间防 GC（与 SETUP 向导同理）
        self._dialog: ProxyDialog | None = None

    def _execute(self) -> None:
        """打开诊断窗并自动跑一次"""
        if self._dialog is not None:
            self._dialog.raise_()
            self._dialog.activateWindow()
            self.logger.debug("诊断窗已存在，置前")
            return

        configured = ""
        try:
            configured = config_manager.get("basic.proxy", str)
        except Exception:  # 配置未就绪按留空处理，不阻塞诊断
            pass

        self.logger.info("打开网络诊断")
        self._dialog = ProxyDialog(configured_proxy=configured, parent=self.gui)
        self._dialog.finished.connect(self._on_closed)
        self._dialog.show()
        self._dialog.start_diagnose()

    def _on_closed(self, _result: int) -> None:
        """释放弹窗引用（closeEvent 已收尾线程）"""
        if self._dialog is not None:
            self._dialog.deleteLater()
            self._dialog = None
