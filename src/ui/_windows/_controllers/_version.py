# src/ui/_windows/_controllers/_version.py
"""版本控制器

- 提供版本检查入口与结果透出
- 探测走独立线程，不占 GUI 线程
"""

import asyncio

from PySide6.QtCore import QThread, Signal

from exceptions import MAP_KEY_VERSION, MAPS, NewVersionError, VersionError
from skin.messages import VersionMessage
from skin.theme import WAIT_DIALOG
from utils.check import ReleaseNote, check_updates, release_history

from ..._dialogs import NoticeDialog, ReleaseNotesDialog, WaitDialog
from ._base import BaseController

_ERR_MAP_VERSION = MAPS[MAP_KEY_VERSION]
_TAG_PREFIX = "v"  # release 标签相对版本号多出的前缀


class _VersionWorker(QThread):
    """版本检查线程

    - 结果以 (文案, 版本清单, 焦点标签, 成败) 发回
    - 发现新版顺带拉发布说明，拉不到即留空清单
    """

    done = Signal(str, list, str, bool)

    def run(self) -> None:
        try:
            ver = asyncio.run(check_updates())
            self.done.emit(WAIT_DIALOG.up_to_date.format(ver=ver), [], "", True)
        except NewVersionError as e:
            tag = f"{_TAG_PREFIX}{e.new_version}"
            notes = self._notes()
            focus = tag if any(note.tag == tag for note in notes) else ""
            self.done.emit(
                _ERR_MAP_VERSION[NewVersionError].format(**vars(e)), notes, focus, True
            )
        except VersionError as e:
            self.done.emit(_ERR_MAP_VERSION[type(e)].format(**vars(e)), [], "", False)
        except Exception as e:
            self.done.emit(
                WAIT_DIALOG.crash_text.format(err=type(e).__name__), [], "", False
            )

    def _notes(self) -> list[ReleaseNote]:
        """发布说明清单，拉不到即空"""
        try:
            return list(asyncio.run(release_history()))
        except Exception:
            return []


class VersionController(BaseController):
    """版本控制器"""

    # 契约声明
    LOGGER_NAME = "GUI.Version"
    BTN_KEY = "version"  # 工具栏接线标识，改名需连动 _misc 与主窗

    def _execute(self) -> None:
        """版本检查

        - 等待窗可取消，关窗即弃用线程
        - 带得到本版正文即直接开双栏弹窗，否则走通知窗文案
        """
        # 面板只记首行摘要，新版提示文案与成败态一并透出
        dialog = WaitDialog(WAIT_DIALOG.check_text, parent=self.gui, cancelable=True)
        worker = _VersionWorker()
        result: list[tuple[str, list, str, bool]] = []

        def _collect(text: str, notes: list, focus: str, passed: bool) -> None:

            # 先存结果再收窗：finish 自动 accept，防暂存被 disconnect 掐断
            result.append((text, notes, focus, passed))
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

        msg, notes, focus, passed = result[0]
        head = next((ln.strip() for ln in msg.splitlines() if ln.strip()), msg)
        if passed:
            self.logger.info(f"版本检查：{head}")
        else:
            self.logger.error(f"版本检查失败：{head}")

        if focus:
            ReleaseNotesDialog.show_release_notes(notes, focus, parent=self.gui)
            return
        NoticeDialog.notify(msg, parent=self.gui, title=VersionMessage.CHECK_TITLE)
