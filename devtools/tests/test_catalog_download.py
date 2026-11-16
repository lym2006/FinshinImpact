"""在线目录取件的单元测试

- 落盘件按目录里的指纹逐样核，不符即删掉半截件
- 镜像按序优先、官方直链兜底，代理地址原样递给取件
- 同名同指纹的本地件在场即不重取
- 核过指纹的件把指纹记进同目录一份索引，索引记过的件能直接拼成可装目标
- 每个源的坏法各记一句，合进一条点名到发行件的说明
"""

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from services.adapter_catalog import ReleaseRow  # noqa: E402
from services.env_setup import wheel_fetch as rel_mod  # noqa: E402

_WHEEL = "finshin_adapter_tg-9.9.9-py3-none-any.whl"
_OFFICIAL = (
    f"https://example.invalid/FinshinAdapterTG/releases/download/v9.9.9/{_WHEEL}"
)
_MIRROR = "https://gh-proxy.com/"
_BODIES = b"wheel bytes for tests"
_SHA = hashlib.sha256(_BODIES).hexdigest()
_MIRRORS = (_MIRROR,)


def _row(url: str = _OFFICIAL, sha256: str = _SHA) -> ReleaseRow:
    """拼一只发行件行"""
    return ReleaseRow(
        distribution="finshin-adapter-tg", version="9.9.9", url=url, sha256=sha256
    )


class TestDownloadRelease(unittest.IsolatedAsyncioTestCase):
    """发行件下载与指纹核验"""

    def setUp(self) -> None:
        """准备一个空的落盘目录"""
        self._pool = tempfile.TemporaryDirectory()
        self.addCleanup(self._pool.cleanup)
        self.target_dir = Path(self._pool.name) / "wheels"

    async def _download(
        self, fetch: AsyncMock, row: ReleaseRow | None = None
    ) -> rel_mod.DownloadOutcome:
        """喂取件替跑一遍下载"""
        with patch.object(rel_mod.GitClient, "get_file", fetch):
            return await rel_mod.download_release(
                row or _row(), self.target_dir, _MIRRORS
            )

    async def test_verified_wheel_lands(self) -> None:
        """指纹相符的件改名落盘并交回路径"""
        fetch = AsyncMock(return_value=_BODIES)
        outcome = await self._download(fetch)
        if outcome.path is None:
            self.fail(f"没落成件：{outcome.note}")

        self.assertEqual(outcome.note, "")
        self.assertEqual(outcome.path.name, _WHEEL)
        self.assertEqual(outcome.path.read_bytes(), _BODIES)
        self.assertEqual(
            sorted(item.name for item in self.target_dir.iterdir()),
            sorted([_WHEEL, rel_mod._INDEX_NAME]),
        )
        self.assertEqual(rel_mod._recorded_digests(self.target_dir)[_WHEEL], _SHA)

    async def test_sha_mismatch_removes_partial(self) -> None:
        """指纹不符即删掉落盘件并报那一步"""
        fetch = AsyncMock(return_value=_BODIES)
        outcome = await self._download(fetch, _row(sha256="f" * 64))
        self.assertIsNone(outcome.path)
        self.assertIn("finshin-adapter-tg", outcome.note)
        self.assertIn("落盘指纹与目录不符", outcome.note)
        self.assertEqual(list(self.target_dir.iterdir()), [])

    async def test_mirrors_before_official(self) -> None:
        """镜像排在官方地址前面，代理原样递下去"""
        fetch = AsyncMock(return_value=_BODIES)
        with patch.object(rel_mod.GitClient, "get_file", fetch):
            await rel_mod.download_release(
                _row(), self.target_dir, _MIRRORS, "http://127.0.0.1:7897"
            )
        fetch.assert_awaited_once()
        self.assertEqual(fetch.call_args.args[0], f"{_MIRROR}{_OFFICIAL}")
        self.assertEqual(fetch.call_args.args[2], "http://127.0.0.1:7897")

    async def test_second_source_succeeds(self) -> None:
        """首个源坏即换下一源，坏法各记一句但整笔算成"""
        fetch = AsyncMock(side_effect=[None, _BODIES])
        outcome = await self._download(fetch)
        if outcome.path is None:
            self.fail(f"换源后仍没落成件：{outcome.note}")

        self.assertEqual(outcome.note, "")
        self.assertEqual(fetch.await_count, 2)

    async def test_all_sources_failed(self) -> None:
        """全部源都坏时点名发行件并列出每个源"""
        fetch = AsyncMock(return_value=None)
        outcome = await self._download(fetch)
        self.assertIsNone(outcome.path)
        self.assertIn("finshin-adapter-tg", outcome.note)
        self.assertIn(_MIRROR + _OFFICIAL, outcome.note)
        self.assertIn(_OFFICIAL, outcome.note)
        self.assertEqual(fetch.await_count, 2)

    async def test_local_wheel_reused(self) -> None:
        """同名同指纹的本地件在场即不重取"""
        self.target_dir.mkdir(parents=True)
        (self.target_dir / _WHEEL).write_bytes(_BODIES)
        fetch = AsyncMock(return_value=None)
        outcome = await self._download(fetch)
        fetch.assert_not_awaited()
        if outcome.path is None:
            self.fail(f"本地件没接上：{outcome.note}")

        self.assertEqual(outcome.note, "")

    async def test_local_wheel_with_wrong_sha_refetched(self) -> None:
        """本地件指纹不符即重新取一次"""
        self.target_dir.mkdir(parents=True)
        (self.target_dir / _WHEEL).write_bytes(b"stale")
        fetch = AsyncMock(return_value=_BODIES)
        outcome = await self._download(fetch)
        fetch.assert_awaited_once()
        if outcome.path is None:
            self.fail(f"重取后没落成件：{outcome.note}")

        self.assertEqual(outcome.path.read_bytes(), _BODIES)

    async def test_bad_file_name_rejected(self) -> None:
        """直链末段不是 wheel 文件名即拒收且不取件"""
        fetch = AsyncMock(return_value=_BODIES)
        outcome = await self._download(
            fetch, _row(url="https://example.com/index.html")
        )
        self.assertIsNone(outcome.path)
        self.assertIn("wheel 文件名", outcome.note)
        fetch.assert_not_awaited()


class TestLocalIndex(unittest.TestCase):
    """本机指纹索引与由它拼出的可装目标"""

    def setUp(self) -> None:
        """准备一个落盘目录与一份件"""
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.root = Path(holder.name)
        (self.root / _WHEEL).write_bytes(_BODIES)

    def _record(self) -> None:
        """按核过的结果记一次指纹"""
        self.assertTrue(rel_mod._record_digest(self.root, _WHEEL, _SHA))

    def test_recorded_wheel_becomes_target(self) -> None:
        """记过指纹的件拼成一行目标，版本取文件名，直链指向盘上那份"""
        self._record()
        target = rel_mod.local_release("finshin-adapter-tg", _WHEEL, self.root)
        if target is None:
            self.fail("记过指纹的件没拼出目标")

        self.assertEqual(target.version, "9.9.9")
        self.assertEqual(target.sha256, _SHA)
        self.assertEqual(Path(target.url).name, _WHEEL)
        self.assertTrue(target.url.startswith("file:"))

    def test_unrecorded_wheel_has_no_target(self) -> None:
        """索引没记那份件即拼不出目标"""
        self.assertIsNone(
            rel_mod.local_release("finshin-adapter-tg", _WHEEL, self.root)
        )

    def test_changed_wheel_is_not_a_target(self) -> None:
        """盘上内容变了即不算记过的那份件"""
        self._record()
        (self.root / _WHEEL).write_bytes(b"other bytes")
        self.assertIsNone(
            rel_mod.local_release("finshin-adapter-tg", _WHEEL, self.root)
        )

    def test_missing_wheel_is_not_a_target(self) -> None:
        """记过但那份件已不在盘上即不交出目标"""
        self._record()
        (self.root / _WHEEL).unlink()
        self.assertIsNone(
            rel_mod.local_release("finshin-adapter-tg", _WHEEL, self.root)
        )

    def test_bad_index_reads_empty(self) -> None:
        """索引不是合法 JSON 即按没记处理"""
        self._record()
        (self.root / rel_mod._INDEX_NAME).write_text("not json", encoding="utf-8")
        self.assertEqual(rel_mod._recorded_digests(self.root), {})

    def test_absent_index_reads_empty(self) -> None:
        """目录不在场即按没记处理"""
        self.assertEqual(rel_mod._recorded_digests(self.root / "no-such-dir"), {})

    def test_repeated_record_keeps_one_entry(self) -> None:
        """同一份件记两次只留一条，别的记条不丢"""
        self._record()
        other = "finshin_sdk-1.0.0-py3-none-any.whl"
        rel_mod._record_digest(self.root, other, "3" * 64)
        self._record()
        table = rel_mod._recorded_digests(self.root)

        self.assertEqual(sorted(table), sorted([_WHEEL, other]))
        self.assertEqual(table[_WHEEL], _SHA)

    def test_version_needs_five_parts(self) -> None:
        """文件名段数不够即读不出版本号"""
        self.assertEqual(rel_mod._version_in_name(_WHEEL), "9.9.9")
        self.assertEqual(rel_mod._version_in_name("two-parts.whl"), "")


if __name__ == "__main__":
    unittest.main()
