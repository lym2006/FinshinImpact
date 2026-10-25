# devtools/tests/test_link_watcher.py
"""链路计时弹窗轮询测试

- 断连即弹、逐拍回写、恢复即收
- 叉号只压本轮，静默压本次运行
- 配置面板开着时抑制弹窗，关掉后仍断连补弹
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from ui import LinkWatcher  # noqa: E402
from utils.network import LinkStatus  # noqa: E402

_UP = LinkStatus(down=False, elapsed=0, retries=0)


def _down(elapsed: int = 1, retries: int = 1) -> LinkStatus:
    """构造断连快照"""
    return LinkStatus(down=True, elapsed=elapsed, retries=retries)


class _FakeDialog:
    """替身弹窗，只记调用"""

    def __init__(self, on_close, on_mute, parent=None) -> None:
        self.on_close = on_close
        self.on_mute = on_mute
        self.parent = parent
        self.shown = 0
        self.hidden = 0
        self.frames = []

    def refresh(self, status: LinkStatus) -> None:
        self.frames.append(status)

    def show(self) -> None:
        self.shown += 1

    def raise_(self) -> None:
        pass

    def activateWindow(self) -> None:  # noqa: N802
        pass

    def hide(self) -> None:
        self.hidden += 1


class _FakeReport:
    """替身链路上报器，快照由测试直接摆"""

    def __init__(self) -> None:
        self.status = _UP

    def snapshot(self) -> LinkStatus:
        return self.status


class TestLinkWatcher(unittest.TestCase):
    """弹收节奏状态机"""

    def setUp(self) -> None:
        self.report = _FakeReport()
        self.dialogs: list[_FakeDialog] = []

        def factory(on_close, on_mute, parent=None):
            dialog = _FakeDialog(on_close=on_close, on_mute=on_mute, parent=parent)
            self.dialogs.append(dialog)
            return dialog

        self._report_patcher = patch(
            "ui._windows._link_watcher.link_report", self.report
        )
        self._dialog_patcher = patch("ui._windows._link_watcher.LinkDialog", factory)
        self._cfg_patcher = patch.object(
            LinkWatcher, "_is_config_open", lambda self: self._test_config_open
        )
        self.addCleanup(self._report_patcher.stop)
        self.addCleanup(self._dialog_patcher.stop)
        self.addCleanup(self._cfg_patcher.stop)
        self._report_patcher.start()
        self._dialog_patcher.start()
        self._cfg_patcher.start()

        self.watcher = LinkWatcher(parent=None)
        self.watcher._test_config_open = False

    def test_healthy_keeps_dialog_closed(self) -> None:
        self.watcher.poll()
        self.watcher.poll()
        self.assertEqual(self.dialogs, [])

    def test_down_shows_at_once_and_reuses_window(self) -> None:
        self.report.status = _down(elapsed=1, retries=2)
        self.watcher.poll()
        self.report.status = _down(elapsed=2, retries=3)
        self.watcher.poll()
        self.assertEqual(len(self.dialogs), 1)
        self.assertEqual(self.dialogs[0].shown, 1)
        self.assertEqual([f.retries for f in self.dialogs[0].frames], [2, 3])

    def test_recovery_closes_at_once(self) -> None:
        self.report.status = _down()
        self.watcher.poll()
        self.report.status = _UP
        self.watcher.poll()
        self.assertEqual(self.dialogs[0].hidden, 1)

    def test_next_cycle_reopens_after_recovery(self) -> None:
        self.report.status = _down()
        self.watcher.poll()
        self.report.status = _UP
        self.watcher.poll()
        self.report.status = _down(elapsed=5, retries=6)
        self.watcher.poll()
        self.assertEqual(len(self.dialogs), 2)

    def test_close_suppresses_only_this_cycle(self) -> None:
        self.report.status = _down()
        self.watcher.poll()
        self.dialogs[0].on_close()

        self.watcher.poll()
        self.assertEqual(len(self.dialogs), 1)

        self.report.status = _UP
        self.watcher.poll()
        self.report.status = _down()
        self.watcher.poll()
        self.assertEqual(len(self.dialogs), 2)

    def test_mute_suppresses_the_rest_of_the_run(self) -> None:
        self.report.status = _down()
        self.watcher.poll()
        self.dialogs[0].on_mute()

        for status in (_UP, _down(), _UP, _down()):
            self.report.status = status
            self.watcher.poll()
        self.assertEqual(len(self.dialogs), 1)

    def test_parent_passed_to_dialog(self) -> None:
        self.report.status = _down()
        self.watcher.poll()
        self.assertIsNone(self.dialogs[0].parent)

    def test_config_open_suppresses_popup(self) -> None:
        self.watcher._test_config_open = True
        self.report.status = _down()
        self.watcher.poll()
        self.watcher.poll()
        self.assertEqual(self.dialogs, [])

    def test_reopen_after_config_closes(self) -> None:
        self.watcher._test_config_open = True
        self.report.status = _down()
        self.watcher.poll()
        self.assertEqual(self.dialogs, [])

        self.watcher._test_config_open = False
        self.watcher.poll()
        self.assertEqual(len(self.dialogs), 1)


if __name__ == "__main__":
    unittest.main()
