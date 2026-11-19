"""版本变化控制器

- 拉取远程 release 正文并按最新一版比对有无新版
- 有新版先提示一句，再照常打开全版本清单
"""

import asyncio
from typing import cast

from PySide6.QtCore import QThread, Signal

from exceptions import NewVersionError, VersionError, describe_error
from skin.theme import RELEASE_NOTES_DIALOG, WAIT_DIALOG
from utils import get_logger
from utils.check import check_latest, release_history

from ..._dialogs import NoticeDialog, ReleaseNotesDialog, WaitDialog
from ._base import BaseController
from ._worker import run_waiting_worker

_logger = get_logger("GUI.ReleaseNotes")


class _ReleaseNotesWorker(QThread):
    """版本变化拉取线程

    - 结果以 (文案, 版本清单, 有无新版, 成败) 发回
    - 比对读不懂版本串按失败处理，不静默
    """

    done = Signal(str, list, bool, bool)

    def run(self) -> None:
        try:
            notes = list(asyncio.run(release_history()))
        except VersionError as e:
            self.done.emit(describe_error(e), [], False, False)
            return
        except Exception as e:
            _logger.debug("版本变化拉取异常", exc_info=True)
            self.done.emit(
                WAIT_DIALOG.crash_text.format(err=type(e).__name__), [], False, False
            )
            return

        try:
            check_latest(notes)
        except NewVersionError as e:
            self.done.emit(describe_error(e), notes, True, True)
        except VersionError as e:
            self.done.emit(describe_error(e), [], False, False)
        else:
            self.done.emit(
                RELEASE_NOTES_DIALOG.ready.format(count=len(notes)), notes, False, True
            )


class ReleaseNotesController(BaseController):
    """版本变化控制器"""

    # 契约声明
    LOGGER_NAME = "GUI.ReleaseNotes"
    BTN_KEY = "release_notes"

    def _execute(self) -> None:
        """拉取版本变化内容

        - 等待窗可取消，关窗即弃用线程
        - 有新版先弹一句提示，再开双栏弹窗
        - 日志只记一行摘要
        """
        dialog = WaitDialog(
            RELEASE_NOTES_DIALOG.loading, parent=self.gui, cancelable=True
        )
        worker = _ReleaseNotesWorker()
        frames = run_waiting_worker(dialog, worker, worker.done)
        if not frames:
            self.logger.info("用户取消版本变化拉取")
            return

        msg, notes, has_update, passed = cast(tuple[str, list, bool, bool], frames[0])
        if not passed:
            self.logger.error(f"版本变化拉取失败：{msg}")
            NoticeDialog.notify(msg, parent=self.gui)
            return

        head = next((ln.strip() for ln in msg.splitlines() if ln.strip()), msg)
        self.logger.info(f"版本变化：{head}")
        if has_update:
            NoticeDialog.notify(msg, parent=self.gui)
        ReleaseNotesDialog.show_release_notes(notes, parent=self.gui)
