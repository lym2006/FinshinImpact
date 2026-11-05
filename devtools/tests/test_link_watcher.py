# devtools/tests/test_link_watcher.py
"""链路计时弹窗轮询测试

- 断连即弹、逐拍回写、恢复即收
- 叉号只压本轮，静默压本次运行
- 面板与检查窗在途时抑制弹窗，收掉后仍断连补弹
"""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
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
            LinkWatcher, "_is_round_open", lambda self: self._test_round_open
        )
        self.addCleanup(self._report_patcher.stop)
        self.addCleanup(self._dialog_patcher.stop)
        self.addCleanup(self._cfg_patcher.stop)
        self._report_patcher.start()
        self._dialog_patcher.start()
        self._cfg_patcher.start()

        self.watcher = LinkWatcher(parent=None)
        self.watcher._test_round_open = False

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
        self.watcher._test_round_open = True
        self.report.status = _down()
        self.watcher.poll()
        self.watcher.poll()
        self.assertEqual(self.dialogs, [])

    def test_reopen_after_config_closes(self) -> None:
        self.watcher._test_round_open = True
        self.report.status = _down()
        self.watcher.poll()
        self.assertEqual(self.dialogs, [])

        self.watcher._test_round_open = False
        self.watcher.poll()
        self.assertEqual(len(self.dialogs), 1)

    def test_suppression_reason_logged_once(self) -> None:
        """压住弹窗的原因同一句只报一次，放行后不补报"""
        self.watcher._test_round_open = True
        self.report.status = _down()
        with self.assertLogs("Bot.GUI.Link", level="DEBUG") as captured:
            self.watcher.poll()
            self.watcher.poll()
        self.assertEqual(
            [r.getMessage() for r in captured.records],
            ["断连计时窗未弹：配置面板或检查窗在途"],
        )

        self.watcher._test_round_open = False
        with self.assertNoLogs("Bot.GUI.Link", level="DEBUG"):
            self.watcher.poll()


class TestRoundOpenProbe(unittest.TestCase):
    """抑制判据实况

    - 面板与检查进度窗任一在途即不弹，两窗同屏会互踩
    """

    def _watcher(self, check_window: object | None) -> LinkWatcher:
        """造一只无面板的轮询器，检查窗替身可控"""
        watcher = LinkWatcher(parent=None)
        watcher._host = SimpleNamespace(findChildren=lambda _cls: [])
        self.check_patcher = patch(
            "ui._windows._link_watcher.current_check_window",
            return_value=check_window,
        )
        self.check_patcher.start()
        self.addCleanup(self.check_patcher.stop)
        return watcher

    def test_no_window_allows_popup(self) -> None:
        watcher = self._watcher(None)
        self.assertFalse(watcher._is_round_open())

    def test_visible_check_window_suppresses(self) -> None:
        watcher = self._watcher(SimpleNamespace(isVisible=lambda: True))
        self.assertTrue(watcher._is_round_open())

    def test_retained_hidden_check_window_allows(self) -> None:
        """收窗不销毁的常驻实例不吃抑制"""
        watcher = self._watcher(SimpleNamespace(isVisible=lambda: False))
        self.assertFalse(watcher._is_round_open())


if __name__ == "__main__":
    unittest.main()
