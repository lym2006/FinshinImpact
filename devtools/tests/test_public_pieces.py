"""接口包公开件测试

- 覆盖未绑定就调用当场报错，本体导入即完成绑定
- 覆盖日志一行落进点名那只日志器，带异常再补一行调试档
- 覆盖断链两句话转达到本体的状态机与计数
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from finshin_sdk import LogLevel, link_down, link_up, log  # noqa: E402
from finshin_sdk import _link as link_module  # noqa: E402
from finshin_sdk import _log as log_module  # noqa: E402
from utils import get_logger  # noqa: E402
from utils.network import link_report  # noqa: E402
from utils.network._link import _DOWN_THRESHOLD  # noqa: E402


class TestLogPiece(unittest.TestCase):
    """日志公开件"""

    def test_host_import_binds_the_sink(self) -> None:
        self.assertIsNotNone(log_module._sink)

    def test_unbound_call_raises(self) -> None:
        with patch.object(log_module, "_sink", None):
            with self.assertRaises(RuntimeError):
                log("Adapter", LogLevel.INFO, "没绑上就写了")

    def test_line_lands_in_the_named_logger(self) -> None:
        with self.assertLogs("Bot.Adapter", level="INFO") as captured:
            log("Adapter", LogLevel.INFO, "一行普通话")
        self.assertEqual(captured.records[0].getMessage(), "一行普通话")
        self.assertEqual(captured.records[0].levelname, "INFO")

    def test_exception_adds_a_debug_line(self) -> None:
        with self.assertLogs("Bot.Adapter", level="DEBUG") as captured:
            log("Adapter", LogLevel.ERROR, "兜住了一处", exc=RuntimeError("炸了"))
        self.assertEqual(
            [record.levelname for record in captured.records], ["ERROR", "DEBUG"]
        )

    def test_public_line_matches_send_error(self) -> None:
        logger = get_logger("Adapter")
        with self.assertLogs("Bot.Adapter", level="DEBUG") as via_public:
            log("Adapter", LogLevel.ERROR, "同一句", exc=RuntimeError("同一只"))
        with self.assertLogs("Bot.Adapter", level="DEBUG") as via_inner:
            logger.send_error("同一句", RuntimeError("同一只"))
        self.assertEqual(
            [(r.levelname, r.getMessage()) for r in via_public.records],
            [(r.levelname, r.getMessage()) for r in via_inner.records],
        )


class TestLinkPiece(unittest.TestCase):
    """断链上报公开件"""

    def setUp(self) -> None:
        link_report.reset("用例起表")
        self.addCleanup(link_report.reset, "用例收尾")

    def test_host_import_binds_the_sinks(self) -> None:
        self.assertIsNotNone(link_module._on_failure)
        self.assertIsNotNone(link_module._on_recovery)

    def test_unbound_calls_raise(self) -> None:
        with patch.object(link_module, "_on_failure", None):
            with self.assertRaises(RuntimeError):
                link_down("GetUpdates", OSError("断了"), None)
        with patch.object(link_module, "_on_recovery", None):
            with self.assertRaises(RuntimeError):
                link_up()

    def test_failures_reach_the_host_counter(self) -> None:
        for _ in range(_DOWN_THRESHOLD):
            link_down("GetUpdates", OSError("断了"), None)
        self.assertTrue(link_report.snapshot().down)
        link_up()
        self.assertFalse(link_report.snapshot().down)


if __name__ == "__main__":
    unittest.main()
