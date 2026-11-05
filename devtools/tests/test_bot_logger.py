# devtools/tests/test_bot_logger.py
"""调试日志调用链取法测试

- 调试记录默认单行，链由调用处点名要
- 报错日志把异常本体与链一起沉进调试记录
"""

import logging
import sys
import unittest
from pathlib import Path
from typing import cast

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from utils.logger import BotLogger  # noqa: E402

_TRACEBACK_HEAD = "Traceback (most recent call last)"


def _render(record: logging.LogRecord) -> str:
    """按默认格式器落出整行，异常链一并算进来"""
    return logging.Formatter("%(message)s").format(record)


class TestDebugChain(unittest.TestCase):
    """调试记录的链由调用处点名"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.logger = cast(BotLogger, logging.getLogger("Bot.TestLogger"))

    def test_exception_in_the_air_stays_single_line(self) -> None:
        try:
            raise OSError("boom")
        except OSError:
            with self.assertLogs("Bot.TestLogger", level="DEBUG") as captured:
                self.logger.debug("存档缺失")
        self.assertEqual(len(captured.records), 1)
        self.assertNotIn(_TRACEBACK_HEAD, _render(captured.records[0]))

    def test_asked_chain_renders(self) -> None:
        try:
            raise OSError("boom")
        except OSError:
            with self.assertLogs("Bot.TestLogger", level="DEBUG") as captured:
                self.logger.debug("探针异常", exc_info=True)
        text = _render(captured.records[0])
        self.assertIn(_TRACEBACK_HEAD, text)
        self.assertIn("OSError: boom", text)


class TestSendErrorChain(unittest.TestCase):
    """报错行的链沉在调试记录里"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.logger = cast(BotLogger, logging.getLogger("Bot.TestSender"))

    def test_panel_line_has_no_chain(self) -> None:
        try:
            raise ValueError("坏在这")
        except ValueError as error:
            with self.assertLogs("Bot.TestSender", level="DEBUG") as captured:
                self.logger.send_error("面板那行", error)
        self.assertEqual(
            [record.levelno for record in captured.records],
            [logging.ERROR, logging.DEBUG],
        )
        self.assertNotIn(_TRACEBACK_HEAD, _render(captured.records[0]))
        self.assertIn(_TRACEBACK_HEAD, _render(captured.records[1]))

    def test_stored_exception_keeps_its_chain(self) -> None:
        """异常存下来、在 except 之外补报时链不丢"""
        caught: ValueError
        try:
            raise ValueError("坏在这")
        except ValueError as error:
            caught = error
        with self.assertLogs("Bot.TestSender", level="DEBUG") as captured:
            self.logger.send_error("面板那行", caught)
        text = _render(captured.records[1])
        self.assertIn(_TRACEBACK_HEAD, text)
        self.assertIn("ValueError: 坏在这", text)


if __name__ == "__main__":
    unittest.main()
