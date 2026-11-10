# src/ui/_windows/_controllers/_release_notes.py
"""版本变化控制器

- 拉取远程 release 正文并展示版本变化内容
"""

import asyncio
from typing import cast

from PySide6.QtCore import QThread, Signal

from exceptions import VersionError, describe_error
from skin.theme import RELEASE_NOTES_DIALOG, WAIT_DIALOG
from utils import get_logger
from utils.check import release_history

from ..._dialogs import NoticeDialog, ReleaseNotesDialog, WaitDialog
from ._base import BaseController
from ._worker import run_waiting_worker

_logger = get_logger("GUI.ReleaseNotes")


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
            self.done.emit(describe_error(e), [], False)
        except Exception as e:
            _logger.debug("版本变化拉取异常", exc_info=True)
            self.done.emit(
                WAIT_DIALOG.crash_text.format(err=type(e).__name__), [], False
            )


class ReleaseNotesController(BaseController):
    """版本变化控制器"""

    # 契约声明
    LOGGER_NAME = "GUI.ReleaseNotes"
    BTN_KEY = "release_notes"

    def _execute(self) -> None:
        """拉取版本变化内容

        - 等待窗可取消，关窗即弃用线程
        - 版本清单交双栏弹窗，面板只记一行摘要
        """
        dialog = WaitDialog(
            RELEASE_NOTES_DIALOG.loading, parent=self.gui, cancelable=True
        )
        worker = _ReleaseNotesWorker()
        frames = run_waiting_worker(dialog, worker, worker.done)
        if not frames:
            self.logger.info("用户取消版本变化拉取")
            return

        msg, notes, passed = cast(tuple[str, list, bool], frames[0])
        if not passed:
            self.logger.error(f"版本变化拉取失败：{msg}")
            NoticeDialog.notify(msg, parent=self.gui)
            return

        self.logger.info(f"版本变化：{msg}")
        ReleaseNotesDialog.show_release_notes(notes, parent=self.gui)
