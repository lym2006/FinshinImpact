# src/ui/_windows/_controllers/_release_notes.py
"""版本变化控制器

- 拉取远程 release 正文并展示版本变化内容
"""

import asyncio

from PySide6.QtCore import QThread, Signal

from exceptions import MAP_KEY_VERSION, MAPS, VersionError
from skin.theme import RELEASE_NOTES_DIALOG, WAIT_DIALOG
from utils.check import release_history

from ..._dialogs import NoticeDialog, ReleaseNotesDialog, WaitDialog
from ._base import BaseController

_ERR_MAP_VERSION = MAPS[MAP_KEY_VERSION]


class _ReleaseNotesWorker(QThread):
    """版本变化拉取线程

    - 结果以 (文案, 版本清单, 成败) 发回
    """

    done = Signal(str, list, bool)

    def run(self) -> None:
        try:
            notes = list(asyncio.run(release_history()))
            self.done.emit(
                RELEASE_NOTES_DIALOG.ready.format(count=len(notes)), notes, True
            )
        except VersionError as e:
            self.done.emit(_ERR_MAP_VERSION[type(e)].format(**vars(e)), [], False)
        except Exception as e:
            self.done.emit(
                WAIT_DIALOG.crash_text.format(err=type(e).__name__), [], False
            )


class ReleaseNotesController(BaseController):
    """版本变化控制器"""

    # 契约声明
    LOGGER_NAME = "GUI.ReleaseNotes"
    BTN_KEY = "release_notes"  # 工具栏接线标识，改名需连动 _misc 与主窗

    def _execute(self) -> None:
        """拉取版本变化内容

        - 等待窗可取消，关窗即弃用线程
        - 版本清单交双栏弹窗，面板只记一行摘要
        """
        dialog = WaitDialog(
            RELEASE_NOTES_DIALOG.loading, parent=self.gui, cancelable=True
        )
        worker = _ReleaseNotesWorker()
        result: list[tuple[str, list, bool]] = []

        def _collect(text: str, notes: list, passed: bool) -> None:

            # 先存结果再收窗：finish 自动 accept，防暂存被 disconnect 掐断
            result.append((text, notes, passed))
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
            self.logger.info("用户取消版本变化拉取")
            return

        msg, notes, passed = result[0]
        if not passed:
            self.logger.error(f"版本变化拉取失败：{msg}")
            NoticeDialog.notify(msg, parent=self.gui)
            return

        self.logger.info(f"版本变化：{msg}")
        ReleaseNotesDialog.show_release_notes(notes, parent=self.gui)
