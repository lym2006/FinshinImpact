"""依赖同步的单元测试

- 同步先 compile 闭包再 sync，装过的开发工具并入保留清单
- 整批失败即返回保留清单全体，开发模式只回手动命令
- 保留清单由核心依赖、已装接口包、适配器声明依赖、已装适配器包与启用插件依赖并成
- 各路里同名只留先读到的一条，让开的那条要交代出来
- 从没保存过勾选的实例也并入随包插件的依赖，表外插件的按勾选算
- 启动器那侧与本体这侧读同一份核心依赖声明，读数不一致即红
"""

import sys
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "packaging"))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

import pack_spec  # noqa: E402

from finshin_sdk.domain import ManifestKey  # noqa: E402
from services import adapter_manifest  # noqa: E402
from services.env_setup import deps_install, deps_keep  # noqa: E402

_KEEP = ["aiogram==3.29.1", "pillow==12.1.1"]
_DEV_PIN = "ruff==0.16.3"


class TestSyncEnv(unittest.TestCase):
    """按保留清单重建环境"""

    def setUp(self) -> None:
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        for name in ("_editable_project_pin", "_interpreter_pins"):
            self.stack.enter_context(patch.object(deps_install, name, return_value=[]))
        self.dev = self.stack.enter_context(
            patch.object(deps_install, "dev_mode", return_value=False)
        )
        self.dev_pins = self.stack.enter_context(
            patch.object(deps_install, "_installed_dev_pins", return_value=[_DEV_PIN])
        )
        self.run = self.stack.enter_context(
            patch.object(deps_install, "with_index_retry", return_value=0)
        )

    def test_success_returns_empty(self) -> None:
        """整链成功返回空失败清单"""
        self.assertEqual(deps_install.sync_env(list(_KEEP)), [])

    def test_dev_pins_still_installed(self) -> None:
        """装过的开发工具仍进 sync 的保留清单"""
        deps_install.sync_env(list(_KEEP))

        self.dev_pins.assert_called_once()

    def test_sync_failure_returns_keep(self) -> None:
        """sync 落空即整批判失败"""
        self.run.return_value = 1

        self.assertEqual(deps_install.sync_env(list(_KEEP)), list(_KEEP))

    def test_compile_failure_skips_sync(self) -> None:
        """闭包编译失败即整批判失败，不再执行 sync"""
        self.run.side_effect = [1]

        self.assertEqual(deps_install.sync_env(list(_KEEP)), list(_KEEP))
        self.run.assert_called_once()

    def test_dev_mode_runs_nothing(self) -> None:
        """开发模式只回手动命令，不执行装卸"""
        self.dev.return_value = True

        self.assertEqual(deps_install.sync_env(list(_KEEP)), list(_KEEP))
        self.run.assert_not_called()


class TestKeepUnion(unittest.TestCase):
    """各路依赖并成的保留清单"""

    def test_adapter_deps_are_kept(self) -> None:
        """适配器声明的库进保留清单，同步环境不删引擎依赖"""
        core = ["pyside6-essentials==6.11.2"]
        sdk = ["finshin-sdk==0.1.0"]
        adapter = ["aiogram==3.29.1"]
        installed = ["finshin-adapter-tg==0.1.0"]
        plugin = ["pillow==12.1.1"]
        with (
            patch.object(deps_keep, "_core_dependencies", lambda: core),
            patch.object(deps_keep, "_installed_sdk_pin", lambda: sdk),
            patch.object(deps_keep, "adapter_deps_union", lambda exclude=None: adapter),
            patch.object(
                deps_keep, "installed_adapter_pins", lambda exclude=None: installed
            ),
            patch.object(deps_keep, "_enabled_deps_union", lambda: plugin),
        ):
            self.assertEqual(
                deps_keep.keep_union(),
                [*core, *sdk, *adapter, *installed, *plugin],
            )

    def test_installed_sdk_survives_without_adapter(self) -> None:
        """一只适配器都不在场时，已装的接口包仍进保留清单

        - 缺这一条，卸掉最后一只适配器再点同步就把接口包删了
        """
        with (
            patch.object(deps_keep, "_core_dependencies", lambda: []),
            patch.object(deps_keep, "adapter_deps_union", lambda exclude=None: []),
            patch.object(deps_keep, "installed_adapter_pins", lambda exclude=None: []),
            patch.object(deps_keep, "_enabled_deps_union", lambda: []),
            patch.object(deps_keep, "installed_version", lambda name: "0.1.0"),
        ):
            self.assertEqual(deps_keep.keep_union(), ["finshin-sdk==0.1.0"])

    def test_absent_sdk_adds_no_pin(self) -> None:
        """接口包不在场时不追加 pin，免得 sync 顺带从索引强装"""
        with patch.object(deps_keep, "installed_version", lambda name: ""):
            self.assertEqual(deps_keep._installed_sdk_pin(), [])

    def test_installed_adapter_survives_sync(self) -> None:
        """只装包、无目录时，适配器包自己与它的顶层依赖都进保留清单

        - 缺任何一条，用户点一次依赖同步就把适配器连引擎库一起删掉
        """
        point = SimpleNamespace(
            name="tg",
            module="finshin_adapter_tg.entry",
            attr="parts",
            dist=SimpleNamespace(
                name="finshin-adapter-tg",
                version="0.1.0",
                requires=["aiogram==3.29.1"],
            ),
        )
        with (
            patch.object(deps_keep, "_core_dependencies", lambda: []),
            patch.object(deps_keep, "_installed_sdk_pin", lambda: []),
            patch.object(deps_keep, "_enabled_deps_union", lambda: []),
            patch.object(adapter_manifest, "_adapters_dir", lambda: None),
            patch.object(adapter_manifest, "_installed_points", lambda: (point,)),
        ):
            self.assertEqual(
                sorted(deps_keep.keep_union()),
                ["aiogram==3.29.1", "finshin-adapter-tg==0.1.0"],
            )


class TestKeepMerge(unittest.TestCase):
    """各路依赖并起来的去重与交代"""

    def _four(self, core, adapter, installed, plugin):
        """把各路依赖换成给定清单，接口包一律先当不在场"""
        return (
            patch.object(deps_keep, "_core_dependencies", lambda: core),
            patch.object(deps_keep, "_installed_sdk_pin", lambda: []),
            patch.object(deps_keep, "adapter_deps_union", lambda exclude=None: adapter),
            patch.object(
                deps_keep, "installed_adapter_pins", lambda exclude=None: installed
            ),
            patch.object(deps_keep, "_enabled_deps_union", lambda: plugin),
        )

    def test_same_pin_kept_once(self) -> None:
        """两处钉的是同一条 pin 时只留一条，也不交代"""
        with ExitStack() as stack:
            for patcher in self._four(["pillow==12.1.1"], ["pillow==12.1.1"], [], []):
                stack.enter_context(patcher)
            self.assertEqual(deps_keep.keep_union(), ["pillow==12.1.1"])
            self.assertEqual(deps_keep.keep_conflicts(), [])

    def test_conflict_keeps_the_first_and_reports(self) -> None:
        """同名不同写法时留先读到的那条，并交代让开的那条

        - 裸包名与钉了版本的写法也算两条不同 pin，各交代一次
        """
        with ExitStack() as stack:
            for patcher in self._four(
                ["httpx==0.28.1"], ["httpx==0.27.0"], [], ["httpx"]
            ):
                stack.enter_context(patcher)
            self.assertEqual(deps_keep.keep_union(), ["httpx==0.28.1"])
            notes = deps_keep.keep_conflicts()

        self.assertEqual(len(notes), 2)
        self.assertIn("httpx", notes[0])
        self.assertIn("httpx==0.28.1", notes[0])
        self.assertIn("httpx==0.27.0", notes[0])

    def test_notes_reach_the_progress_window(self) -> None:
        """同步任务开工前先把交代行打出来"""
        lines: list[str] = []

        with (
            patch.object(deps_install, "dev_mode", return_value=True),
            patch.object(deps_install, "_installed_dev_pins", lambda: []),
            patch.object(deps_install, "_editable_project_pin", lambda: []),
            patch.object(deps_install, "_interpreter_pins", lambda: []),
        ):
            deps_install.sync_env(["httpx==0.28.1"], lines.append, ["说明一行"])

        self.assertEqual(lines[0], "说明一行")


class TestInstanceEnabledUnion(unittest.TestCase):
    """全实例启用插件的依赖并集"""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.instances = Path(self._tmp.name)
        self.instance = self.instances / "tg.000001"
        self.instance.mkdir()
        self.help_row = {
            ManifestKey.NAME: "help",
            ManifestKey.DEPS: ["foo==1.0"],
        }
        self.web_row = {
            ManifestKey.NAME: "webshot",
            ManifestKey.DEPS: ["markdown==3.10.2"],
        }
        patcher = patch.object(deps_keep, "INSTANCES_DIR", self.instances)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _union(self, manifests: list[dict]) -> list[str]:
        """按给定的清单读数跑一遍启用并集"""
        with (
            patch.object(deps_keep, "plugins_roots", lambda: [self.instance]),
            patch.object(deps_keep, "load_manifests", lambda roots: manifests),
        ):
            return deps_keep._enabled_deps_union()

    def test_missing_state_keeps_bundled_deps(self) -> None:
        """实例从没保存过勾选，随包插件的依赖照样并入保留清单

        - 整台跳过会让随包插件的库被一次同步删掉，启动即缺件
        """
        self.assertEqual(self._union([self.help_row, self.web_row]), ["foo==1.0"])

    def test_empty_enabled_keeps_bundled_deps(self) -> None:
        """保存过勾选且一只表外插件都没选，同样并入随包插件的依赖"""
        (self.instance / "plugins.toml").write_text(
            'enabled = []\ncatalog = "dig"', encoding="utf-8"
        )

        self.assertEqual(self._union([self.help_row, self.web_row]), ["foo==1.0"])

    def test_missing_state_drops_external_deps(self) -> None:
        """没保存过勾选时表外插件不在场，它的依赖不并入"""
        self.assertEqual(self._union([self.web_row]), [])

    def test_saved_choice_adds_external_deps(self) -> None:
        """勾过的表外插件依赖并进同一份清单"""
        (self.instance / "plugins.toml").write_text(
            'enabled = ["webshot"]\ncatalog = "dig"', encoding="utf-8"
        )

        self.assertEqual(
            self._union([self.help_row, self.web_row]),
            ["foo==1.0", "markdown==3.10.2"],
        )


class TestDeclarationsParity(unittest.TestCase):
    """启动器那侧与本体这侧读同一份核心依赖"""

    def test_the_two_sides_agree_on_the_real_tree(self) -> None:
        """对真实仓根，两侧读出的核心依赖是同一些"""
        root = Path(__file__).resolve().parents[2]
        shell = set(pack_spec.dependencies(root))
        body = set(deps_keep._core_dependencies())
        self.assertTrue(shell, "两侧都读了个空，这条锁不住任何东西")
        self.assertEqual(shell, body)


if __name__ == "__main__":
    unittest.main()
