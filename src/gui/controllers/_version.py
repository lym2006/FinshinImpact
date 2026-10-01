# src/gui/controllers/_version.py
"""版本控制器

- 提供检查更新入口与结果透出
- 探测走独立线程，不占 GUI 线程
"""

import asyncio

from PySide6.QtCore import QThread, Signal

from exceptions import MAPS, NewVersionError, VersionError
from utils.version_checker import check_updates

from .._theme import WAIT_DIALOG
from ..dialogs import NoticeDialog, WaitDialog
from ._base import BaseController

_ERR_MAP_VERSION = MAPS["Version"]


class _VersionWorker(QThread):
    """版本检查线程

    - 结果以 (文案, 成败) 发回
    """

    done = Signal(str, bool)

    def run(self) -> None:
        try:
            ver = asyncio.run(check_updates())
            self.done.emit(WAIT_DIALOG.up_to_date.format(ver=ver), True)
        except VersionError as e:
            msg = _ERR_MAP_VERSION[type(e)].format(**vars(e))
            self.done.emit(msg, isinstance(e, NewVersionError))
        except Exception as e:
            self.done.emit(WAIT_DIALOG.crash_text.format(err=type(e).__name__), False)


class VersionController(BaseController):
    """版本控制器"""

    # ==================== 契约声明 ====================

    LOGGER_NAME = "GUI.Version"
    BTN_KEY = "update"  # 工具栏接线标识，与按钮表同源，改名需连动 _misc 与主窗

    # ==================== 业务逻辑实现 ====================

    def _execute(self) -> None:
        """检查版本更新

        - 转圈窗可取消（关窗即弃线程）
        - 结果经统一通知弹窗承载全文
        """
        # 面板只记首行摘要，新版提示文案与成败态同源透出
        dialog = WaitDialog(WAIT_DIALOG.check_text, parent=self.gui, cancelable=True)
        worker = _VersionWorker()
        result: list[tuple[str, bool]] = []

        def _collect(text: str, passed: bool) -> None:

            # 先存文案再收窗：finish 自动 accept，防暂存被 disconnect 掐断
            result.append((text, passed))
            dialog.finish(text, passed)

        worker.done.connect(_collect)
        worker.start()
        try:
            dialog.exec()
        finally:
            # 用户先行关窗：摘除回执防迟到结果触碰已关窗口
            worker.done.disconnect()
            worker.requestInterruption()
            worker.wait()

        if not result:
            self.logger.info("用户取消版本检查")
            return

        msg, passed = result[0]
        head = next((ln.strip() for ln in msg.splitlines() if ln.strip()), msg)
        if passed:
            self.logger.info(f"版本检查：{head}")
        else:
            self.logger.error(f"版本检查失败：{head}")
        NoticeDialog.notify(msg, parent=self.gui)
