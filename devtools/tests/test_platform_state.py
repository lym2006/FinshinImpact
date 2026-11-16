"""平台组件读数的单元测试

- 三档归属按本机来路、本机版本与在线版本比出来
- 版本串读不懂、在线不比本机新、源码仓挂着且已装包都算本机已有
- 该装的那批只收本机没有与在线更新的两档
- 接口包没到位或高出上限时适配器那颗不给装，接口包那行自己不受此限
- 在场平台只看已装包，源码仓挂着没装的不算
"""

import sys
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from finshin_sdk.domain import Platform  # noqa: E402
from services.adapter_catalog import Catalog, ReleaseRow  # noqa: E402
from services.adapter_manifest import InstalledAdapter  # noqa: E402
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


def _tg_row(installed: str, online: str, tree: bool = False) -> mod.ComponentRow:
    """按本机在场版本、在线版本与来路排出一行读数"""
    item = _adapter(installed) if installed else None
    tree_names = {Platform.TELEGRAM: _ADAPTER} if tree else {}
    with (
        patch.object(
            mod, "installed_adapters", lambda: () if item is None else (item,)
        ),
        patch.object(mod, "tree_distributions", lambda: tree_names),
        patch.object(mod, "load_adapter_manifests", lambda: {}),
        patch.object(mod, "installed_version", lambda name: ""),
    ):
        rows = mod.component_rows(_catalog(online))

    return next(row for row in rows if row.platform == str(Platform.TELEGRAM))


def _rows(sdk: str, adapter: str) -> tuple[mod.ComponentRow, ...]:
    """接口包与 Telegram 各一行读数，本机在场版本按点名给"""
    item = _adapter(adapter) if adapter else None
    with (
        patch.object(
            mod, "installed_adapters", lambda: () if item is None else (item,)
        ),
        patch.object(mod, "tree_distributions", lambda: {}),
        patch.object(mod, "load_adapter_manifests", lambda: {}),
        patch.object(mod, "installed_version", lambda name: sdk),
    ):
        return mod.component_rows(_catalog("0.1.0"))


def _adapter_row(rows: tuple[mod.ComponentRow, ...]) -> mod.ComponentRow:
    """读数里 Telegram 那一行"""
    return next(row for row in rows if row.platform == str(Platform.TELEGRAM))


def _sdk_row(rows: tuple[mod.ComponentRow, ...]) -> mod.ComponentRow:
    """读数里接口包那一行"""
    return next(row for row in rows if not row.platform)


class TestBucket(unittest.TestCase):
    """一行组件归到哪一档"""

    def test_newer_online_is_upgradable(self) -> None:
        """在线比本机新即进可更新"""
        self.assertEqual(
            _tg_row("0.1.0", "0.1.1").bucket, mod.ComponentBucket.UPGRADABLE
        )

    def test_same_version_is_local(self) -> None:
        """版本相等即已到位"""
        self.assertEqual(_tg_row("0.1.0", "0.1.0").bucket, mod.ComponentBucket.LOCAL)

    def test_older_online_is_local(self) -> None:
        """在线比本机旧即不动，不提示降级"""
        self.assertEqual(_tg_row("0.2.0", "0.1.0").bucket, mod.ComponentBucket.LOCAL)

    def test_absent_package_is_online(self) -> None:
        """本机没在场即只在网络"""
        self.assertEqual(_tg_row("", "0.1.0").bucket, mod.ComponentBucket.ONLINE)

    def test_tree_source_is_local(self) -> None:
        """源码仓挂着且已装包即本机已有，在线再新也不给装"""
        self.assertEqual(
            _tg_row("0.1.0", "0.1.1", tree=True).bucket, mod.ComponentBucket.LOCAL
        )

    def test_tree_source_without_package_is_online(self) -> None:
        """源码仓挂着但没装包即仍算只在网络，还要给装"""
        self.assertEqual(
            _tg_row("", "0.1.0", tree=True).bucket, mod.ComponentBucket.ONLINE
        )

    def test_unreadable_version_is_local(self) -> None:
        """版本串读不懂算本机已有，不拿猜的新版去装"""
        self.assertEqual(_tg_row("最新", "0.1.0").bucket, mod.ComponentBucket.LOCAL)


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
        with patch.object(mod, "_declared_requires", lambda: requires):
            rows = _rows("0.1.0", "0.1.0")
        self.assertEqual(
            mod.install_blocked(rows, _adapter_row(rows)),
            "先更新接口包",
        )

    def test_sdk_over_ceiling_blocks(self) -> None:
        """接口包高出适配器写的上限，那句换成接口包太新"""
        requires = {str(Platform.TELEGRAM): "<0.0.1"}
        with patch.object(mod, "_declared_requires", lambda: requires):
            rows = _rows("0.1.0", "0.1.0")
        self.assertEqual(
            mod.install_blocked(rows, _adapter_row(rows)),
            "接口包太新，适配器等新版",
        )

    def test_sdk_in_range_frees(self) -> None:
        """接口包落在要求的区间之内即放行"""
        requires = {str(Platform.TELEGRAM): ">=0.1.0,<0.2.0"}
        with patch.object(mod, "_declared_requires", lambda: requires):
            rows = _rows("0.1.5", "0.1.0")
        self.assertEqual(mod.install_blocked(rows, _adapter_row(rows)), "")

    def test_requires_line_keeps_both_bounds(self) -> None:
        """要求那一行把上下限原样带出来"""
        requires = {str(Platform.TELEGRAM): ">=0.1.0,<0.2.0"}
        with (
            patch.object(mod, "_declared_requires", lambda: requires),
            patch.object(mod, "installed_version", lambda name: "0.2.0"),
        ):
            text = mod.deps_text(_adapter_row(_rows("0.2.0", "0.1.0")))
        self.assertEqual(text, "要求 >=0.1.0,<0.2.0，本机 0.2.0 未满足")


class TestPresentPlatforms(unittest.TestCase):
    """选窗认的在场平台"""

    def test_lists_installed_platform_only(self) -> None:
        """已装适配器的那一平台进表，接口包那行不进"""
        with ExitStack() as stack:
            for patcher in (
                patch.object(mod, "installed_adapters", lambda: (_adapter("0.1.0"),)),
                patch.object(mod, "tree_distributions", lambda: {}),
                patch.object(mod, "load_adapter_manifests", lambda: {}),
                patch.object(mod, "installed_version", lambda name: "0.1.0"),
            ):
                stack.enter_context(patcher)
            self.assertEqual(mod.present_platforms(), frozenset({"tg"}))

    def test_tree_without_package_is_absent(self) -> None:
        """源码仓挂着但没装包的平台不进表"""
        with ExitStack() as stack:
            for patcher in (
                patch.object(mod, "installed_adapters", lambda: ()),
                patch.object(
                    mod, "tree_distributions", lambda: {Platform.TELEGRAM: _ADAPTER}
                ),
                patch.object(mod, "load_adapter_manifests", lambda: {}),
                patch.object(mod, "installed_version", lambda name: ""),
            ):
                stack.enter_context(patcher)
            self.assertEqual(mod.present_platforms(), frozenset())


if __name__ == "__main__":
    unittest.main()
