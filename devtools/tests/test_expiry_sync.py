# devtools/tests/test_expiry_sync.py
"""到期记录与上下文同步清除测试

- 记录文件到期即交出同键会话键，未到期的不动
- 按键清上下文逐键累加，键不在库内即零
- 清理循环一轮把到期记录与同键上下文一起作废
- 历史清理起手落记号，删不净即留着它，记号在才补一遍
- 真库的外键级联由 devtools/tests/test_data_layer.py 自证
"""

import asyncio
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from core.domain.ids import SessionKey  # noqa: E402
from plugins.AI.core import _store  # noqa: E402
from plugins.AI.services import _monitor  # noqa: E402

_DAY = 86400.0
_KEEP = 30 * _DAY
_AGE = 40 * _DAY


def _stamp(path: Path, age: float) -> None:
    """把落盘时间挪到指定秒数之前"""
    now = time.time()
    os.utime(path, (now - age, now - age))


def _logger_stub() -> SimpleNamespace:
    """吞掉日志的假记录器"""
    return SimpleNamespace(info=lambda *_: None, send_error=lambda *_: None)


class TestPurgeRecords(unittest.TestCase):
    """到期记录只认文件自己的时间"""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.patchers = [
            patch.object(_monitor, "_logger", _logger_stub()),
            patch.object(
                _monitor,
                "ai_config",
                SimpleNamespace(keep_seconds=_KEEP, record_dir=self.root),
            ),
        ]
        for patcher in self.patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_expired_yields_session_key(self) -> None:
        """到期文件被删并把会话键交回"""
        gone = self.root / "tg.g100123.md"
        gone.write_text("旧问答", encoding="utf8")
        _stamp(gone, _AGE)

        keys = _monitor._purge_records(time.time() - _KEEP)

        self.assertEqual(keys, (SessionKey("tg.g100123"),))
        self.assertFalse(gone.exists())

    def test_unexpired_keeps_both(self) -> None:
        """没到期的文件不动也不交键"""
        live = self.root / "tg.u456.md"
        live.write_text("新问答", encoding="utf8")

        keys = _monitor._purge_records(time.time() - _KEEP)

        self.assertEqual(keys, ())
        self.assertTrue(live.exists())

    def test_legacy_name_still_returns_its_stem(self) -> None:
        """旧的按人分开的文件名照删，交回的键在库里对不上"""
        legacy = self.root / "tg.g100123.456.md"
        legacy.write_text("旧形态", encoding="utf8")
        _stamp(legacy, _AGE)

        keys = _monitor._purge_records(time.time() - _KEEP)

        self.assertEqual(keys, (SessionKey("tg.g100123.456"),))

    def test_undeletable_file_yields_no_key(self) -> None:
        """删不掉的记录不交键，免得清掉还留着的上下文"""
        for name in ("tg.g999.md", "tg.g888.md"):
            (self.root / name).mkdir()
        for name in ("tg.g999.md", "tg.g888.md"):
            _stamp(self.root / name, _AGE)

        keys = _monitor._purge_records(time.time() - _KEEP)

        self.assertEqual(keys, ())


class _Repo:
    """只记删除调用的假仓储"""

    def __init__(self, known: set[str]) -> None:
        self._known = known
        self.deleted: list[str] = []
        self.deleted_all = 0

    async def delete(self, session_key: str) -> int:
        self.deleted.append(session_key)
        return 1 if session_key in self._known else 0

    async def delete_all(self) -> int:
        self.deleted_all += 1
        return 0


def _value(obj: object):
    """交出返回该对象的协程替身"""

    async def _fake() -> object:
        return obj

    return _fake


class TestPurgeSessions(unittest.IsolatedAsyncioTestCase):
    """按会话键清上下文"""

    async def test_sums_every_key(self) -> None:
        """逐键删，条数按命中数累加"""
        repo = _Repo({"tg.g100123"})
        with patch.object(_store, "_repo", _value(repo)):
            removed = await _store.purge_sessions(
                (SessionKey("tg.g100123"), SessionKey("tg.u456"))
            )

        self.assertEqual(removed, 1)
        self.assertEqual(repo.deleted, ["tg.g100123", "tg.u456"])

    async def test_empty_keys_touch_nothing(self) -> None:
        """没有到期记录即不碰库"""
        repo = _Repo({"tg.g100123"})
        with patch.object(_store, "_repo", _value(repo)):
            removed = await _store.purge_sessions(())

        self.assertEqual(removed, 0)
        self.assertEqual(repo.deleted, [])


class TestCleanupRound(unittest.IsolatedAsyncioTestCase):
    """清理循环一轮把两边一起作废"""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.sessions: list[tuple[SessionKey, ...]] = []
        self.resumed = 0

        async def _purge_sessions(keys: tuple[SessionKey, ...]) -> int:
            self.sessions.append(keys)
            return len(keys)

        async def _purge_idle(_before: float) -> int:
            return 0

        async def _resume() -> None:
            self.resumed += 1

        async def _stop_sleep(_seconds: float) -> None:
            raise asyncio.CancelledError

        self.patchers = [
            patch.object(_monitor, "_logger", _logger_stub()),
            patch.object(
                _monitor,
                "ai_config",
                SimpleNamespace(
                    keep_seconds=_KEEP, waiting_time=0.0, record_dir=self.root
                ),
            ),
            patch.object(_monitor, "purge_sessions", _purge_sessions),
            patch.object(_monitor, "purge_idle_sessions", _purge_idle),
            patch.object(_monitor, "purge_pending", _resume),
            patch.object(_monitor.asyncio, "sleep", _stop_sleep),
        ]
        for patcher in self.patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

    async def _run_once(self) -> None:
        with self.assertRaises(asyncio.CancelledError):
            await _monitor.cleanup_loop()

    async def test_expired_record_clears_same_key(self) -> None:
        """到期记录被删时同键上下文一起清"""
        expired = self.root / "tg.g100123.md"
        expired.write_text("旧问答", encoding="utf8")
        _stamp(expired, _AGE)
        live = self.root / "tg.u456.md"
        live.write_text("新问答", encoding="utf8")

        await self._run_once()

        self.assertFalse(expired.exists())
        self.assertTrue(live.exists())
        self.assertEqual(self.sessions, [(SessionKey("tg.g100123"),)])

    async def test_nothing_expired_passes_empty_keys(self) -> None:
        """一条都没到期时交空键序列"""
        live = self.root / "tg.u456.md"
        live.write_text("新问答", encoding="utf8")

        await self._run_once()

        self.assertEqual(self.sessions, [()])

    async def test_resume_runs_once_before_scanning(self) -> None:
        """补完断掉的清理排在首轮扫描之前，只跑一次"""
        await self._run_once()

        self.assertEqual(self.resumed, 1)


class TestPurgeHistoryMark(unittest.IsolatedAsyncioTestCase):
    """历史清理的记号只在中断时留下"""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = _Repo(set())
        self.mark = self.root / _store._PENDING_MARK
        self.patchers = [
            patch.object(_store, "_logger", _logger_stub()),
            patch.object(_store, "ai_config", SimpleNamespace(record_dir=self.root)),
            patch.object(_store, "_repo", _value(self.repo)),
        ]
        for patcher in self.patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

    async def test_clean_purge_revokes_mark(self) -> None:
        """库与记录一起清成即撤记号"""
        record = self.root / "tg.g100123.md"
        record.write_text("旧问答", encoding="utf8")

        await _store.purge_history()

        self.assertFalse(record.exists())
        self.assertFalse(self.mark.exists())
        self.assertEqual(self.repo.deleted_all, 1)

    async def test_undeletable_record_keeps_mark(self) -> None:
        """记录删不掉即留着记号，下次启动照着它补"""
        (self.root / "tg.g999.md").mkdir()

        await _store.purge_history()

        self.assertTrue(self.mark.exists())

    async def test_mark_resume_clears_and_revokes(self) -> None:
        """记号在即补一遍并撤掉它"""
        self.mark.touch()

        await _store.purge_pending()

        self.assertEqual(self.repo.deleted_all, 1)
        self.assertFalse(self.mark.exists())

    async def test_no_mark_clears_nothing(self) -> None:
        """没记号即什么都没断，库一次都不碰"""
        await _store.purge_pending()

        self.assertEqual(self.repo.deleted_all, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
