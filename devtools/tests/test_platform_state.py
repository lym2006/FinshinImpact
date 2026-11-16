"""平台组件读数的单元测试

- 行的拼装、归属档与装挡判定同一条链路，两份模块一起过
- 版本串读不懂、在线不比本机新、源码仓挂着且已装包都算本机已有
- 该装的那批只收本机没有与在线更新的两档
- 接口包没到位或高出上限时适配器那颗不给装，接口包那行自己不受此限
- 在场平台只看已装包，源码仓挂着没装的不算
- 版本清单逐版报本机来路，盘上的件逐份报在不在清单里
"""

import hashlib
import sys
import tempfile
import unittest
from contextlib import ExitStack
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from finshin_sdk.domain import Platform  # noqa: E402
from services.adapter_catalog import Catalog, ReleaseRow  # noqa: E402
from services.adapter_manifest import InstalledAdapter  # noqa: E402
from services.env_setup import platform_rows as rows_mod  # noqa: E402
from services.env_setup import platform_state as mod  # noqa: E402

_ADAPTER = "finshin-adapter-tg"
_SHA = "0" * 64


def _adapter(version: str) -> InstalledAdapter:
    """一只已装的 Telegram 适配器包"""
    return InstalledAdapter(
        platform=Platform.TELEGRAM,
        distribution=_ADAPTER,
        version=version,
        requires=("aiogram==3.29.1", "finshin-sdk>=0.1.0"),
        entry="finshin_adapter_tg.entry",
    )


def _catalog(version: str) -> Catalog:
    """只列 Telegram 一行目录的清单"""
    return Catalog(
        sdk=None,
        adapters={
            Platform.TELEGRAM: ReleaseRow(
                distribution=_ADAPTER,
                version=version,
                url=f"https://example.invalid/{_ADAPTER}.whl",
                sha256=_SHA,
            )
        },
        rejects=(),
    )


def _tg_row(installed: str, online: str, tree: bool = False) -> rows_mod.ComponentRow:
    """按本机在场版本、在线版本与来路排出一行读数"""
    item = _adapter(installed) if installed else None
    tree_names = {Platform.TELEGRAM: _ADAPTER} if tree else {}
    with (
        patch.object(
            rows_mod, "installed_adapters", lambda: () if item is None else (item,)
        ),
        patch.object(rows_mod, "tree_distributions", lambda: tree_names),
        patch.object(rows_mod, "load_adapter_manifests", lambda: {}),
        patch.object(rows_mod, "installed_version", lambda name: ""),
    ):
        rows = rows_mod.component_rows(_catalog(online))

    return next(row for row in rows if row.platform == str(Platform.TELEGRAM))


def _rows(sdk: str, adapter: str) -> tuple[rows_mod.ComponentRow, ...]:
    """接口包与 Telegram 各一行读数，本机在场版本按点名给"""
    item = _adapter(adapter) if adapter else None
    with (
        patch.object(
            rows_mod, "installed_adapters", lambda: () if item is None else (item,)
        ),
        patch.object(rows_mod, "tree_distributions", lambda: {}),
        patch.object(rows_mod, "load_adapter_manifests", lambda: {}),
        patch.object(rows_mod, "installed_version", lambda name: sdk),
    ):
        return rows_mod.component_rows(_catalog("0.1.0"))


def _adapter_row(rows: tuple[rows_mod.ComponentRow, ...]) -> rows_mod.ComponentRow:
    """读数里 Telegram 那一行"""
    return next(row for row in rows if row.platform == str(Platform.TELEGRAM))


def _sdk_row(rows: tuple[rows_mod.ComponentRow, ...]) -> rows_mod.ComponentRow:
    """读数里接口包那一行"""
    return next(row for row in rows if not row.platform)


_WHEEL_BODY = b"wheel body"


def _release_row(version: str, sha: str) -> ReleaseRow:
    """一行目录，直链末段按版本号拼出 wheel 文件名"""
    stem = _ADAPTER.replace("-", "_")

    return ReleaseRow(
        distribution=_ADAPTER,
        version=version,
        url=f"https://example.invalid/{stem}-{version}-py3-none-any.whl",
        sha256=sha,
    )


def _wheel_on(root: Path, version: str) -> str:
    """在临时目录落一份 wheel 件，交出它的指纹"""
    stem = _ADAPTER.replace("-", "_")
    (root / f"{stem}-{version}-py3-none-any.whl").write_bytes(_WHEEL_BODY)

    return hashlib.sha256(_WHEEL_BODY).hexdigest()


def _multi_row(installed: str, *versions: ReleaseRow) -> rows_mod.ComponentRow:
    """一行读数，目录行内按给定次序带版本清单"""
    newest, *_older = versions
    release = replace(newest, versions=tuple(versions))

    return rows_mod.ComponentRow(
        platform=str(Platform.TELEGRAM),
        distribution=_ADAPTER,
        source=rows_mod.ComponentSource.INSTALLED,
        installed=installed,
        requires="",
        release=release,
        bucket=rows_mod.ComponentBucket.UPGRADABLE,
    )


class TestOlderVersions(unittest.TestCase):
    """版本清单里除最新一版外的每一版"""

    def setUp(self) -> None:
        """临时 wheel 目录，0.2.0 那份件在场"""
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self._root = Path(holder.name)
        self._cached = _wheel_on(self._root, "0.2.0")

    def _row(self, installed: str) -> rows_mod.ComponentRow:
        """最新 0.3.0，清单里另有 0.2.0 与 0.1.0 两版"""
        return _multi_row(
            installed,
            _release_row("0.3.0", _SHA),
            _release_row("0.2.0", self._cached),
            _release_row("0.1.0", _SHA),
        )

    def test_latest_is_not_listed(self) -> None:
        """清单只报更早的那几版，最新一版由版本行说"""
        with patch.object(mod, "WHEELS_DIR", self._root):
            lines = mod.older_versions(self._row("0.1.0"))

        self.assertEqual([line.release.version for line in lines], ["0.2.0", "0.1.0"])

    def test_installed_version_is_marked(self) -> None:
        """本机环境里就是那一版即标出来"""
        with patch.object(mod, "WHEELS_DIR", self._root):
            lines = mod.older_versions(self._row("0.2.0"))

        self.assertEqual([line.installed for line in lines], [True, False])

    def test_matching_digest_is_cached(self) -> None:
        """盘上那份件指纹对得上目录即算已下载"""
        with patch.object(mod, "WHEELS_DIR", self._root):
            lines = mod.older_versions(self._row("0.3.0"))

        self.assertEqual([line.cached for line in lines], [True, False])

    def test_wrong_digest_is_not_cached(self) -> None:
        """盘上同名那份件指纹对不上即不算已下载"""
        row = _multi_row(
            "0.1.0",
            _release_row("0.3.0", _SHA),
            _release_row("0.2.0", "f" * 64),
        )
        with patch.object(mod, "WHEELS_DIR", self._root):
            lines = mod.older_versions(row)

        self.assertEqual([line.cached for line in lines], [False])

    def test_no_row_lists_nothing(self) -> None:
        """没有目录行即没有清单可列"""
        row = _multi_row("0.1.0", _release_row("0.1.0", _SHA))
        row = replace(row, release=None)
        with patch.object(mod, "WHEELS_DIR", self._root):
            self.assertEqual(mod.older_versions(row), ())


class TestLocalWheels(unittest.TestCase):
    """盘上件的逐份读数"""

    def setUp(self) -> None:
        """临时 wheel 目录，落两份件，其中一份不在清单里"""
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self._root = Path(holder.name)
        self._listed = _wheel_on(self._root, "0.2.0")
        _wheel_on(self._root, "0.0.9")

    def _row(self) -> rows_mod.ComponentRow:
        """清单里只有 0.3.0 与 0.2.0 两版"""
        return _multi_row(
            "0.1.0",
            _release_row("0.3.0", _SHA),
            _release_row("0.2.0", self._listed),
        )

    def test_files_are_listed_by_name(self) -> None:
        """盘上属于这只发行件的件逐份报出"""
        with patch.object(mod, "WHEELS_DIR", self._root):
            lines = mod.local_wheels(self._row())

        self.assertEqual(
            [line.file_name for line in lines],
            [
                "finshin_adapter_tg-0.0.9-py3-none-any.whl",
                "finshin_adapter_tg-0.2.0-py3-none-any.whl",
            ],
        )

    def test_file_in_list_is_marked(self) -> None:
        """文件名对得上清单某一版的即算在清单里"""
        with patch.object(mod, "WHEELS_DIR", self._root):
            lines = mod.local_wheels(self._row())

        self.assertEqual([line.listed for line in lines], [False, True])

    def test_no_row_leaves_files_unmarked(self) -> None:
        """没有目录行时盘上的件一律算对不上"""
        row = replace(self._row(), release=None)
        with patch.object(mod, "WHEELS_DIR", self._root):
            lines = mod.local_wheels(row)

        self.assertEqual([line.listed for line in lines], [False, False])


class TestBucket(unittest.TestCase):
    """一行组件归到哪一档"""

    def test_newer_online_is_upgradable(self) -> None:
        """在线比本机新即进可更新"""
        self.assertEqual(
            _tg_row("0.1.0", "0.1.1").bucket, rows_mod.ComponentBucket.UPGRADABLE
        )

    def test_same_version_is_local(self) -> None:
        """版本相等即已到位"""
        self.assertEqual(
            _tg_row("0.1.0", "0.1.0").bucket, rows_mod.ComponentBucket.LOCAL
        )

    def test_older_online_is_local(self) -> None:
        """在线比本机旧即不动，不提示降级"""
        self.assertEqual(
            _tg_row("0.2.0", "0.1.0").bucket, rows_mod.ComponentBucket.LOCAL
        )

    def test_absent_package_is_online(self) -> None:
        """本机没在场即只在网络"""
        self.assertEqual(_tg_row("", "0.1.0").bucket, rows_mod.ComponentBucket.ONLINE)

    def test_tree_source_is_local(self) -> None:
        """源码仓挂着且已装包即本机已有，在线再新也不给装"""
        self.assertEqual(
            _tg_row("0.1.0", "0.1.1", tree=True).bucket, rows_mod.ComponentBucket.LOCAL
        )

    def test_tree_source_without_package_is_online(self) -> None:
        """源码仓挂着但没装包即仍算只在网络，还要给装"""
        self.assertEqual(
            _tg_row("", "0.1.0", tree=True).bucket, rows_mod.ComponentBucket.ONLINE
        )

    def test_unreadable_version_is_local(self) -> None:
        """版本串读不懂算本机已有，不拿猜的新版去装"""
        self.assertEqual(
            _tg_row("最新", "0.1.0").bucket, rows_mod.ComponentBucket.LOCAL
        )


class TestDistributionName(unittest.TestCase):
    """块首行接的发行件名"""

    def test_tree_declaration_names_the_row(self) -> None:
        """挂载仓那份声明交得出名，没装包也不空着"""
        self.assertEqual(_tg_row("", "0.1.0", tree=True).distribution, _ADAPTER)


class TestUpdateTargets(unittest.TestCase):
    """一键更新的那批目录行"""

    def test_local_row_excluded(self) -> None:
        """本机已有的行不进差集"""
        self.assertEqual(mod.update_targets([_tg_row("0.1.0", "0.1.0")]), [])

    def test_upgradable_row_included(self) -> None:
        """可更新的行进差集，交的是目录行自带的直链与指纹"""
        targets = mod.update_targets([_tg_row("0.1.0", "0.1.1")])
        self.assertEqual([release.version for release in targets], ["0.1.1"])
        self.assertEqual([release.distribution for release in targets], [_ADAPTER])

    def test_online_row_excluded(self) -> None:
        """本机没装过的不进一键，装哪个平台由逐行的按钮定"""
        self.assertEqual(mod.update_targets([_tg_row("", "0.1.0")]), [])


class TestInstallBlocked(unittest.TestCase):
    """接口包不在要求的区间内时适配器那颗不给装，并交出那句下一步"""

    def test_absent_sdk_blocks_the_adapter(self) -> None:
        """本机没装接口包即挡住，那句是先装接口包"""
        rows = _rows("", "")
        self.assertEqual(
            mod.install_blocked(rows, _adapter_row(rows)),
            "先装接口包",
        )

    def test_installed_sdk_frees_the_adapter(self) -> None:
        """接口包在场即放行"""
        rows = _rows("0.1.0", "")
        self.assertEqual(mod.install_blocked(rows, _adapter_row(rows)), "")

    def test_sdk_row_is_never_blocked(self) -> None:
        """接口包那一行不受这条限制，它自己就是出路"""
        rows = _rows("", "")
        self.assertEqual(mod.install_blocked(rows, _sdk_row(rows)), "")

    def test_sdk_below_range_blocks(self) -> None:
        """接口包在场但够不到适配器要求的下限，那句换成先更新接口包"""
        requires = {str(Platform.TELEGRAM): ">=9.9.9"}
        with patch.object(rows_mod, "_declared_requires", lambda: requires):
            rows = _rows("0.1.0", "0.1.0")
        self.assertEqual(
            mod.install_blocked(rows, _adapter_row(rows)),
            "先更新接口包",
        )

    def test_sdk_over_ceiling_blocks(self) -> None:
        """接口包高出适配器写的上限，那句换成接口包太新"""
        requires = {str(Platform.TELEGRAM): "<0.0.1"}
        with patch.object(rows_mod, "_declared_requires", lambda: requires):
            rows = _rows("0.1.0", "0.1.0")
        self.assertEqual(
            mod.install_blocked(rows, _adapter_row(rows)),
            "接口包太新，适配器等新版",
        )

    def test_sdk_in_range_frees(self) -> None:
        """接口包落在要求的区间之内即放行"""
        requires = {str(Platform.TELEGRAM): ">=0.1.0,<0.2.0"}
        with patch.object(rows_mod, "_declared_requires", lambda: requires):
            rows = _rows("0.1.5", "0.1.0")
        self.assertEqual(mod.install_blocked(rows, _adapter_row(rows)), "")

    def test_requires_line_keeps_both_bounds(self) -> None:
        """要求那一行把上下限原样带出来"""
        requires = {str(Platform.TELEGRAM): ">=0.1.0,<0.2.0"}
        with (
            patch.object(rows_mod, "_declared_requires", lambda: requires),
            patch.object(mod, "installed_version", lambda name: "0.2.0"),
        ):
            text = mod.deps_text(_adapter_row(_rows("0.2.0", "0.1.0")))
        self.assertEqual(text, ">=0.1.0,<0.2.0，本机接口包 0.2.0 未满足")


class TestPresentPlatforms(unittest.TestCase):
    """选窗认的在场平台"""

    def test_lists_installed_platform_only(self) -> None:
        """已装适配器的那一平台进表，接口包那行不进"""
        with ExitStack() as stack:
            for patcher in (
                patch.object(
                    rows_mod, "installed_adapters", lambda: (_adapter("0.1.0"),)
                ),
                patch.object(rows_mod, "tree_distributions", lambda: {}),
                patch.object(rows_mod, "load_adapter_manifests", lambda: {}),
                patch.object(rows_mod, "installed_version", lambda name: "0.1.0"),
            ):
                stack.enter_context(patcher)
            self.assertEqual(rows_mod.present_platforms(), frozenset({"tg"}))

    def test_tree_without_package_is_absent(self) -> None:
        """源码仓挂着但没装包的平台不进表"""
        with ExitStack() as stack:
            for patcher in (
                patch.object(rows_mod, "installed_adapters", lambda: ()),
                patch.object(
                    rows_mod,
                    "tree_distributions",
                    lambda: {Platform.TELEGRAM: _ADAPTER},
                ),
                patch.object(rows_mod, "load_adapter_manifests", lambda: {}),
                patch.object(rows_mod, "installed_version", lambda name: ""),
            ):
                stack.enter_context(patcher)
            self.assertEqual(rows_mod.present_platforms(), frozenset())


if __name__ == "__main__":
    unittest.main()
