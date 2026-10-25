# devtools/tests/test_deps_sync.py
"""启动期依赖对账的单元测试

- 对账戳缺失或与声明清单指纹不符即提示同步
- 戳只认声明清单，同步时追加的开发工具与解释器基建不进指纹
- 同步成功才落戳，失败与开发模式都不落
- 启动接线只在对账判为需要时才调同步入口，对账落定才清下载缓存
"""

import sys
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from services.env_setup import deps_install  # noqa: E402

_KEEP = ["aiogram==3.29.1", "pillow==12.1.1"]
_DEV_PIN = "ruff==0.16.3"


class _StampBase(unittest.TestCase):
    """把对账戳与保留清单换成临时盘上的可控值"""

    def setUp(self) -> None:
        stage = tempfile.TemporaryDirectory(prefix="finshin-stamp-")
        self.addCleanup(stage.cleanup)
        self.stamp = Path(stage.name) / ".synced"
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(deps_install, "_SYNC_STAMP", self.stamp))
        self.keep = self.stack.enter_context(
            patch.object(deps_install, "keep_union", return_value=list(_KEEP))
        )
        self.dev = self.stack.enter_context(
            patch.object(deps_install, "dev_mode", return_value=False)
        )

    def write_stamp(self, keep: list[str]) -> None:
        """按给定清单写对账戳"""
        self.stamp.write_text(deps_install._keep_digest(keep), encoding="utf-8")


class TestSyncNeeded(_StampBase):
    """对账判定"""

    def test_missing_stamp_needs_sync(self) -> None:
        """戳从未来过即视为待同步"""
        self.assertTrue(deps_install.sync_needed())

    def test_matching_stamp_skips(self) -> None:
        """戳与当前清单指纹一致即免提示"""
        self.write_stamp(_KEEP)

        self.assertFalse(deps_install.sync_needed())

    def test_order_insensitive(self) -> None:
        """清单顺序变动不改指纹，不误报待同步"""
        self.write_stamp(list(reversed(_KEEP)))

        self.assertFalse(deps_install.sync_needed())

    def test_changed_union_needs_sync(self) -> None:
        """清单增删即指纹变化，重新提示同步"""
        self.write_stamp(["aiogram==3.29.1"])

        self.assertTrue(deps_install.sync_needed())

    def test_no_uv_needs_no_sync(self) -> None:
        """找不到任何 uv 时降级手动命令，缺戳也不提示"""
        self.dev.return_value = True

        self.assertFalse(deps_install.sync_needed())


class TestSyncEnvStamp(_StampBase):
    """同步成功后落戳"""

    def setUp(self) -> None:
        super().setUp()
        for name in ("_editable_project_pin", "_interpreter_pins"):
            self.stack.enter_context(patch.object(deps_install, name, return_value=[]))
        self.dev_pins = self.stack.enter_context(
            patch.object(deps_install, "_installed_dev_pins", return_value=[_DEV_PIN])
        )
        self.run = self.stack.enter_context(
            patch.object(deps_install, "with_index_retry", return_value=0)
        )

    def test_success_writes_declared_digest(self) -> None:
        """整链成功按声明清单落戳，追加的开发工具不进指纹"""
        self.assertEqual(deps_install.sync_env(list(_KEEP)), [])

        self.assertEqual(
            self.stamp.read_text(encoding="utf-8"),
            deps_install._keep_digest(_KEEP),
        )

    def test_dev_pins_still_installed(self) -> None:
        """装过的开发工具仍进 sync 的保留清单"""
        deps_install.sync_env(list(_KEEP))

        self.dev_pins.assert_called_once()

    def test_sync_failure_keeps_stamp_absent(self) -> None:
        """sync 落空即失败，戳缺失下次启动再问"""
        self.run.return_value = 1

        failed = deps_install.sync_env(list(_KEEP))

        self.assertEqual(failed, list(_KEEP))
        self.assertFalse(self.stamp.exists())

    def test_compile_failure_keeps_stamp_absent(self) -> None:
        """闭包编译失败整批判失败，不写成功戳"""
        self.run.side_effect = [1]

        failed = deps_install.sync_env(list(_KEEP))

        self.assertEqual(failed, list(_KEEP))
        self.assertFalse(self.stamp.exists())

    def test_dev_mode_writes_nothing(self) -> None:
        """开发模式只回手动命令，既不执行也不落戳"""
        self.dev.return_value = True

        self.assertEqual(deps_install.sync_env(list(_KEEP)), list(_KEEP))
        self.assertFalse(self.stamp.exists())


class TestStartupWiring(unittest.TestCase):
    """启动链只在对账判需要时才调同步入口，对账落定才清下载缓存"""

    def setUp(self) -> None:
        import bootstrap._slot as slot
        import ui

        self.slot = slot
        self.sync = patch.object(ui, "sync_deps")
        self.mock_sync = self.sync.start()
        self.addCleanup(self.sync.stop)
        self.clean = patch("services.env_setup.subprocess_ops.clean_cache")
        self.mock_clean = self.clean.start()
        self.addCleanup(self.clean.stop)

    def patch_needed(self, *results: bool) -> None:
        """按调用次序给定对账结论"""
        stub = patch(
            "services.env_setup.deps_install.sync_needed", side_effect=list(results)
        )
        stub.start()
        self.addCleanup(stub.stop)

    def test_no_prompt_when_in_sync(self) -> None:
        """指纹相符即不弹同步窗，缓存也不动"""
        self.patch_needed(False)

        self.slot._sync_if_stale()

        self.mock_sync.assert_not_called()
        self.mock_clean.assert_not_called()

    def test_prompt_when_stale(self) -> None:
        """指纹不符才调现有的同步入口"""
        self.patch_needed(True, True)

        self.slot._sync_if_stale()

        self.mock_sync.assert_called_once()

    def test_cache_kept_when_not_reconciled(self) -> None:
        """选否或同步失败都不清缓存，留着下次续装命中"""
        self.patch_needed(True, True)

        self.slot._sync_if_stale()

        self.mock_clean.assert_not_called()

    def test_cache_cleaned_after_reconcile(self) -> None:
        """同步落戳后才清启动器留下的下载缓存"""
        self.patch_needed(True, False)

        self.slot._sync_if_stale()

        self.mock_sync.assert_called_once()
        self.mock_clean.assert_called_once()


if __name__ == "__main__":
    unittest.main()
