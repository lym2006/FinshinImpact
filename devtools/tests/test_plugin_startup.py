# devtools/tests/test_plugin_startup.py
"""启动结算编排的单元测试

- 判定纯实测：pip 包与资源逐项查盘，出补装计划
- 计划为空即免结算，进度窗一次都不开
- 补装只喂实测缺失项，只装不删
- 失败项命中哪个插件就禁用哪个，命中不了全禁，禁用不动已装库
"""

import sys
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from core.domain import ManifestKey, StateKey  # noqa: E402
from ui._guide import _startup  # noqa: E402

_SENTINEL = Path("plugins-sentinel")
_RENDER = {
    ManifestKey.NAME: "AI_render",
    ManifestKey.CORE: False,
    ManifestKey.DEPS: ["markdown==3.10.2", "playwright==1.62.0"],
    ManifestKey.ASSETS: ["playwright chromium-headless-shell"],
}
_AI = {
    ManifestKey.NAME: "AI",
    ManifestKey.CORE: True,
    ManifestKey.DEPS: [],
    ManifestKey.ASSETS: [],
}

_PATCHED = (
    "plugins_root",
    "load_manifests",
    "load_state",
    "catalog_digest",
    "is_pin_installed",
    "is_asset_installed",
    "install_deps",
    "install_assets",
    "save_state",
    "dev_mode",
    "run_with_progress",
    "ensure_app",
    "QMessageBox",
)


class _StartupBase(unittest.TestCase):
    """把结算模块的协作方全部换成 mock"""

    def setUp(self) -> None:
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.m: dict[str, MagicMock] = {}
        for name in _PATCHED:
            self.m[name] = self.stack.enter_context(patch.object(_startup, name))
        self.m["plugins_root"].return_value = _SENTINEL
        self.m["load_manifests"].return_value = [_AI, _RENDER]
        self.m["load_state"].return_value = {StateKey.ENABLED: ["AI_render"]}
        self.m["dev_mode"].return_value = False
        self.m["is_pin_installed"].return_value = True
        self.m["is_asset_installed"].return_value = True


class TestCollectMissing(_StartupBase):
    """补装计划收集"""

    def test_all_present_plan_empty(self) -> None:
        """包与资源实测全齐，计划为空"""
        self.assertEqual(_startup._collect_missing("AAAA"), [])

    def test_missing_pin_planned(self) -> None:
        """只把实测缺失的 pin 列入计划"""
        self.m["is_pin_installed"].side_effect = lambda pin: pin == "markdown==3.10.2"

        plan = _startup._collect_missing("AAAA")

        self.assertEqual(plan, [("AI_render", ["playwright==1.62.0"], [])])

    def test_missing_asset_planned(self) -> None:
        """资源探活落空即列入计划"""
        self.m["is_asset_installed"].return_value = False

        plan = _startup._collect_missing("AAAA")

        self.assertEqual(
            plan, [("AI_render", [], ["playwright chromium-headless-shell"])]
        )

    def test_core_plugin_always_checked(self) -> None:
        """启用集为空也覆盖 core 插件的缺失"""
        self.m["load_state"].return_value = {StateKey.ENABLED: []}
        core = {
            ManifestKey.NAME: "help",
            ManifestKey.CORE: True,
            ManifestKey.DEPS: ["foo==1.0"],
            ManifestKey.ASSETS: [],
        }
        self.m["load_manifests"].return_value = [core]
        self.m["is_pin_installed"].return_value = False

        plan = _startup._collect_missing("AAAA")

        self.assertEqual(plan, [("help", ["foo==1.0"], [])])


class TestSettleRuntime(_StartupBase):
    """结算闸门"""

    def test_no_missing_never_opens_window(self) -> None:
        """什么都不缺就绝不弹结算窗"""
        _startup.settle_runtime("AAAA")

        self.m["run_with_progress"].assert_not_called()

    def test_missing_opens_window(self) -> None:
        """有缺失即起进度窗按计划补装"""
        self.m["is_pin_installed"].side_effect = lambda pin: pin == "markdown==3.10.2"
        self.m["run_with_progress"].return_value = []

        _startup.settle_runtime("AAAA")

        self.m["run_with_progress"].assert_called_once()

    def test_dev_mode_skips(self) -> None:
        """开发模式不自动装卸，恒免结算"""
        self.m["dev_mode"].return_value = True
        self.m["is_pin_installed"].return_value = False

        _startup.settle_runtime("AAAA")

        self.m["run_with_progress"].assert_not_called()

    def test_failure_disables_and_popups(self) -> None:
        """补装失败禁用命中插件并弹窗告知"""
        self.m["is_asset_installed"].return_value = False
        self.m["run_with_progress"].return_value = [
            "playwright chromium-headless-shell"
        ]
        self.m["catalog_digest"].return_value = "cat"

        _startup.settle_runtime("AAAA")

        self.m["save_state"].assert_called_once_with("AAAA", [], "cat")
        self.m["QMessageBox"].return_value.exec.assert_called_once()


class TestInstallMissing(_StartupBase):
    """补装执行"""

    def test_installs_only_missing_items(self) -> None:
        """按计划逐插件补装，只喂缺失项"""
        plan = [("AI_render", ["playwright==1.62.0"], ["playwright chromium"])]
        self.m["install_deps"].return_value = []
        self.m["install_assets"].return_value = []

        failed = _startup._install_missing(plan, None)

        self.assertEqual(failed, [])
        self.m["install_deps"].assert_called_once_with(["playwright==1.62.0"], None)
        self.m["install_assets"].assert_called_once_with(["playwright chromium"], None)

    def test_collects_failed_items(self) -> None:
        """两路失败项合并回传"""
        plan = [("AI_render", ["a==1.0"], ["playwright chromium"])]
        self.m["install_deps"].return_value = ["a==1.0"]
        self.m["install_assets"].return_value = ["playwright chromium"]

        failed = _startup._install_missing(plan, None)

        self.assertEqual(failed, ["a==1.0", "playwright chromium"])


class TestDisableFailed(_StartupBase):
    """失败禁用编排"""

    def setUp(self) -> None:
        super().setUp()
        self.m["catalog_digest"].return_value = "cat"

    def test_drops_plugin_matched_by_dep(self) -> None:
        """失败项命中某插件的依赖，只禁该插件并落盘剩余启用集"""
        self.m["load_state"].return_value = {StateKey.ENABLED: ["AI_render", "other"]}
        other = {
            ManifestKey.NAME: "other",
            ManifestKey.CORE: False,
            ManifestKey.DEPS: ["foo==1.0"],
            ManifestKey.ASSETS: [],
        }
        self.m["load_manifests"].return_value = [_AI, _RENDER, other]

        dropped = _startup._disable_failed("AAAA", ["playwright==1.62.0"])

        self.assertEqual(dropped, ["AI_render"])
        self.m["save_state"].assert_called_once_with("AAAA", ["other"], "cat")

    def test_drops_plugin_matched_by_asset(self) -> None:
        """失败项是资源声明串，同样命中所属插件"""
        dropped = _startup._disable_failed(
            "AAAA", ["playwright chromium-headless-shell"]
        )

        self.assertEqual(dropped, ["AI_render"])

    def test_unmatched_failure_drops_all_enabled(self) -> None:
        """失败项命中不了具体插件（整轮异常），启用集全禁"""
        dropped = _startup._disable_failed("AAAA", ["任务异常中止"])

        self.assertEqual(dropped, ["AI_render"])
        self.m["save_state"].assert_called_once_with("AAAA", [], "cat")

    def test_no_enabled_no_write(self) -> None:
        """启用集为空无需落盘"""
        self.m["load_state"].return_value = {StateKey.ENABLED: []}

        dropped = _startup._disable_failed("AAAA", ["playwright==1.62.0"])

        self.assertEqual(dropped, [])
        self.m["save_state"].assert_not_called()

    def test_root_missing_returns_empty(self) -> None:
        """插件目录定位失败直接空手而归"""
        self.m["plugins_root"].return_value = None

        self.assertEqual(_startup._disable_failed("AAAA", ["x==1.0"]), [])


if __name__ == "__main__":
    unittest.main()
