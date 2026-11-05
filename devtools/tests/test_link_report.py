# devtools/tests/test_link_report.py
"""链路状态上报测试

- 连续失败达阈值才报断连短句，单条失败只记明细、恢复零输出
- 面板与日志的重连计数不含首次失败
- 快照读数、计时起点、周期作废与作废原因各测一组
"""

import logging
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from aiogram.exceptions import TelegramBadRequest, TelegramNetworkError  # noqa: E402
from aiogram.methods import GetMe  # noqa: E402
from aiohttp import ClientError  # noqa: E402
from aiohttp_socks import (  # noqa: E402
    ProxyConnectionError,
    ProxyError,
    ProxyTimeoutError,
)

from adapters.telegram.session import is_link_failure  # noqa: E402
from utils.network import _link as link_module  # noqa: E402
from utils.network._link import (  # noqa: E402
    _DOWN_THRESHOLD,
    _FAIL_LOG_EVERY,
    _RETRY_OFFSET,
    LinkStatus,
    _LinkReport,
    _span_of,
    _timer_of,
)


class TestTimerOf(unittest.TestCase):
    """弹窗计时串两档形态"""

    CASES = (
        (0, "00:00"),
        (9, "00:09"),
        (59, "00:59"),
        (60, "01:00"),
        (65, "01:05"),
        (3599, "59:59"),
        (3600, "01:00:00"),
        (3660, "01:01:00"),
    )

    def test_two_tiers(self) -> None:
        for seconds, expect in self.CASES:
            with self.subTest(seconds):
                self.assertEqual(_timer_of(seconds), expect)


class TestSpanOf(unittest.TestCase):
    """面板时长短串三档换算"""

    CASES = (
        (0, "0 秒"),
        (59, "59 秒"),
        (60, "1 分 00 秒"),
        (65, "1 分 05 秒"),
        (3599, "59 分 59 秒"),
        (3600, "1 时 00 分"),
        (3660, "1 时 01 分"),
    )

    def test_three_tiers(self) -> None:
        for seconds, expect in self.CASES:
            with self.subTest(seconds):
                self.assertEqual(_span_of(seconds), expect)


class TestIsLinkFailure(unittest.TestCase):
    """链路层判定"""

    LINK = (
        ProxyConnectionError("x"),
        ProxyTimeoutError("x"),
        ProxyError("x"),
        ClientError("x"),
        TelegramNetworkError(method=GetMe(), message="x"),
        ConnectionRefusedError("x"),
    )
    SERVER_OR_BUG = (
        TelegramBadRequest(method=GetMe(), message="x"),
        TypeError("x"),
        ValueError("x"),
    )

    def test_connection_errors_count_as_link_failure(self) -> None:
        for exc in self.LINK:
            with self.subTest(type(exc).__name__):
                self.assertTrue(is_link_failure(exc))

    def test_server_answers_and_bugs_do_not(self) -> None:
        for exc in self.SERVER_OR_BUG:
            with self.subTest(type(exc).__name__):
                self.assertFalse(is_link_failure(exc))


class _Clock:
    """测试用的表，指针由用例自己拨"""

    def __init__(self) -> None:
        self.now = 0.0

    def monotonic(self) -> float:
        return self.now


class TestLinkReport(unittest.TestCase):
    """断连与恢复的上报节奏"""

    # 断连日志要说得出走的哪一路，用例统一喂一个代理串
    PROXY = "http://127.0.0.1:7897"
    # 秒，约 147 小时，拨成开机以来的读数，盯住「空档被算成断连」
    UPTIME = 529_223.0

    def setUp(self) -> None:
        self.link = _LinkReport()

    def _emit(self, times: int, level: str = "DEBUG") -> list[logging.LogRecord]:
        """跑 times 次失败并收集日志记录"""
        with self.assertLogs("Bot.Net", level=level) as captured:
            for _ in range(times):
                self.link.failed("GetUpdates", OSError("boom"), self.PROXY)
        return list(captured.records)

    def test_single_failure_stays_quiet(self) -> None:
        """未到阈值的单条失败只记明细，不报断连、快照不归 down"""
        records = self._emit(1)
        self.assertEqual([r.levelno for r in records], [logging.DEBUG])
        self.assertIn(
            f"链路失败：GetUpdates 通道={self.PROXY} OSError: boom",
            records[0].getMessage(),
        )
        self.assertFalse(self.link.snapshot().down)

    def test_blip_then_recovery_logs_nothing(self) -> None:
        """单条抖动后立刻恢复，面板不留任何断连/恢复行"""
        self.link.failed("GetUpdates", OSError("boom"), self.PROXY)
        with self.assertNoLogs("Bot.Net", level="DEBUG"):
            self.link.recovered()

    def test_second_failure_declares_down(self) -> None:
        """连续失败到阈值才起表报断连，明细先于短句且短句带通道"""
        records = self._emit(_DOWN_THRESHOLD)
        errors = [r for r in records if r.levelno == logging.ERROR]
        self.assertEqual(len(errors), 1)
        self.assertIn("引擎断线", errors[0].getMessage())
        self.assertIn(f"通道={self.PROXY}", errors[0].getMessage())
        self.assertTrue(self.link.snapshot().down)

    def test_intermediate_failures_stay_quiet(self) -> None:
        """已断连后、未到下个补报里程碑的失败只记明细"""
        self._emit(_DOWN_THRESHOLD + 2)
        with self.assertLogs("Bot.Net", level="DEBUG") as captured:
            self.link.failed("GetUpdates", OSError("boom"), self.PROXY)
        self.assertEqual([r.levelno for r in captured.records], [logging.DEBUG])
        self.assertIn("链路失败：GetUpdates", captured.records[0].getMessage())

    def test_milestone_failure_logged(self) -> None:
        records = self._emit(_FAIL_LOG_EVERY)
        last = records[-1].getMessage()
        self.assertEqual(records[-1].levelno, logging.DEBUG)
        self.assertIn(f"第 {_FAIL_LOG_EVERY - _RETRY_OFFSET} 次尝试", last)
        self.assertIn("已断 0 秒", last)

    def test_broadcast_lines_carry_no_traceback(self) -> None:
        """异常在场时断网回合的每一行都不带调用链"""
        try:
            raise OSError("boom")
        except OSError as error:
            with self.assertLogs("Bot.Net", level="DEBUG") as captured:
                for _ in range(_FAIL_LOG_EVERY):
                    self.link.failed("GetUpdates", error, self.PROXY)
                self.link.reset("引擎停止")
        broadcasts = [
            record
            for record in captured.records
            if "链路失败" in record.getMessage() or "重连中" in record.getMessage()
        ]
        voided = [
            record
            for record in captured.records
            if "断连周期作废" in record.getMessage()
        ]
        self.assertEqual(len(broadcasts), _FAIL_LOG_EVERY + 1)
        self.assertEqual(len(voided), 1)
        self.assertFalse(any(record.exc_info for record in captured.records))

    def test_recovery_reports_once_then_quiet(self) -> None:
        self._emit(2)
        with self.assertLogs("Bot.Net", level="DEBUG") as captured:
            self.link.recovered()
        panel = [r for r in captured.records if r.levelno >= logging.INFO]
        self.assertEqual(len(panel), 1)
        self.assertIn("网络恢复成功：断线 0 秒，重试 1 次", panel[0].getMessage())
        with self.assertNoLogs("Bot.Net", level="INFO"):
            self.link.recovered()

    def test_success_without_failure_is_silent(self) -> None:
        with self.assertNoLogs("Bot.Net", level="DEBUG"):
            self.link.recovered()

    def test_snapshot_zero_when_healthy(self) -> None:
        status = self.link.snapshot()
        self.assertFalse(status.down)
        self.assertEqual((status.elapsed, status.retries), (0, 0))
        self.assertEqual(status.timer_text, "00:00")

    def test_snapshot_counts_the_cycle(self) -> None:
        """弹窗首拍的读数是第 1 次重连，不含那条原始请求"""
        self.link.failed("GetUpdates", OSError("boom"), self.PROXY)
        self.link.failed("GetUpdates", OSError("boom"), self.PROXY)
        status = self.link.snapshot()
        self.assertTrue(status.down)
        self.assertEqual(status.retries, _DOWN_THRESHOLD - _RETRY_OFFSET)
        self.assertEqual(status.elapsed, 0)
        self.assertEqual(status.span_text, "0 秒")

    def test_clock_starts_on_the_first_failure(self) -> None:
        """计时起点落在本周期第一次失败，界面读不到开机以来的空档"""
        clock = _Clock()
        clock.now = self.UPTIME
        with patch.object(link_module, "time", clock):
            self.link.failed("GetUpdates", OSError("boom"), self.PROXY)
            clock.now = self.UPTIME + 20.0
            self.link.failed("GetUpdates", OSError("boom"), self.PROXY)
            status = self.link.snapshot()
        self.assertEqual(status.elapsed, 20)

    def test_new_cycle_restarts_the_clock(self) -> None:
        """上一轮收尾后另起一轮，时长从新一轮第一次失败起算"""
        clock = _Clock()
        with patch.object(link_module, "time", clock):
            clock.now = 100.0
            self.link.failed("GetUpdates", OSError("boom"), self.PROXY)
            self.link.failed("GetUpdates", OSError("boom"), self.PROXY)
            clock.now = 900.0
            self.link.recovered()
            clock.now = 1000.0
            self.link.failed("GetUpdates", OSError("boom"), self.PROXY)
            self.link.failed("GetUpdates", OSError("boom"), self.PROXY)
            clock.now = 1005.0
            status = self.link.snapshot()
        self.assertEqual(status.elapsed, 5)

    def test_reset_makes_recovery_quiet(self) -> None:
        """作废周期后恢复不再补收尾行，服务停止不留陈旧计时"""
        self.link.failed("GetUpdates", OSError("boom"), self.PROXY)
        self.link.reset("引擎停止")
        self.assertFalse(self.link.snapshot().down)
        with self.assertNoLogs("Bot.Net", level="INFO"):
            self.link.recovered()

    def test_reset_names_who_voided_the_cycle(self) -> None:
        """在途周期被作废即报作废方与累计次数，没在途即无声"""
        self.link.failed("GetUpdates", OSError("boom"), self.PROXY)
        with self.assertLogs("Bot.Net", level="DEBUG") as captured:
            self.link.reset("引擎线程收尾")
        self.assertEqual(
            captured.records[0].getMessage(),
            "断连周期作废：引擎线程收尾（作废前累计 1 次失败）",
        )
        with self.assertNoLogs("Bot.Net", level="DEBUG"):
            self.link.reset("引擎停止")


class TestLinkStatusTexts(unittest.TestCase):
    """快照两串各自形态"""

    def test_timer_and_span_diverge_after_hour(self) -> None:
        status = LinkStatus(down=True, elapsed=3660, retries=7)
        self.assertEqual(status.timer_text, "01:01:00")
        self.assertEqual(status.span_text, "1 时 01 分")


async def _link_fail(self: object, bot: object, method: object, timeout: int) -> None:
    """替父类请求抛一条链路层异常"""
    raise TelegramNetworkError(method=GetMe(), message="链路断了")


class TestSessionLinkReporting(unittest.IsolatedAsyncioTestCase):
    """会话上报开关

    - 探测会话不进断连状态机，引擎会话照旧上报
    """

    async def _make_request(self, report_link: bool) -> None:
        from aiogram import Bot
        from aiogram.client.session.aiohttp import AiohttpSession

        from adapters.telegram.session import SSLUnverifiedSession

        session = SSLUnverifiedSession(proxy=None, report_link=report_link)
        bot = Bot(token="123:abc", session=session)
        with patch.object(AiohttpSession, "make_request", _link_fail):
            with self.assertRaises(TelegramNetworkError):
                await session.make_request(bot, GetMe())

    async def test_probe_session_stays_off_the_counter(self) -> None:
        with self.assertNoLogs("Bot.Net", level="DEBUG"):
            await self._make_request(False)

    async def test_engine_session_reports_failure(self) -> None:
        with self.assertLogs("Bot.Net", level="DEBUG") as captured:
            await self._make_request(True)
        self.assertIn("链路失败：GetMe 通道=直连", captured.records[0].getMessage())


if __name__ == "__main__":
    unittest.main()
