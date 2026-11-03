# devtools/tests/test_log_rollover.py
"""日志文件轮转兜底测试

- 改名被占用挡住即本轮不轮转，行照写进原文件
- 占用没挡住时按份数留旧文件
"""

import logging
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from utils.logger import _handler  # noqa: E402
from utils.logger._handler import create_file_handler  # noqa: E402

_FORMAT = logging.Formatter("%(message)s")
_LIMIT = 64  # 测试用的单文件上限（字节）
_LONG_LINE = "x" * 80


def _emit(handler: logging.Handler, text: str) -> None:
    """喂一条记录给处理器"""
    record = logging.LogRecord("Bot.Test", logging.INFO, __file__, 1, text, (), None)
    handler.handle(record)


class TestRolloverBlocked(unittest.TestCase):
    """原文件被别的进程打开时不丢行"""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "debug.log"

    def _make_handler(self) -> logging.Handler:
        with patch.object(_handler, "_MAX_BYTES", _LIMIT):
            handler = create_file_handler(_FORMAT, self.path)
        self.addCleanup(handler.close)
        return handler

    def test_blocked_rollover_keeps_writing_same_file(self) -> None:
        """改名被挡即继续往原文件追加，且不产生备份"""
        handler = self._make_handler()
        _emit(handler, "seed")
        blocker = self.path.open(encoding="utf-8")
        self.addCleanup(blocker.close)

        _emit(handler, _LONG_LINE)

        self.assertIn(_LONG_LINE, self.path.read_text(encoding="utf-8"))
        self.assertFalse((self.path.parent / "debug.log.1").exists())

    def test_unblocked_rollover_keeps_backup(self) -> None:
        """没人占用时照常轮转，旧内容进备份"""
        handler = self._make_handler()
        _emit(handler, "seed")

        _emit(handler, _LONG_LINE)

        backup = self.path.parent / "debug.log.1"
        self.assertTrue(backup.exists())
        self.assertIn("seed", backup.read_text(encoding="utf-8"))
        self.assertNotIn("seed", self.path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
