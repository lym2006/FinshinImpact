# devtools/tests/test_plugin_manifest.py
"""插件清单恒启用与档位的单元测试

- 清单只认 name/title/summary/deps/assets/help
- 恒启用与加载档位来自随包表，多写的键按未知键忽略
- 引导期精简实现与运行期读取在这两条上一致
- 引导期根表认外部目录，同名插件以仓内那行为准
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from core.domain import INSTALLED_PLUGINS_NAME, PLUGINS_PKG  # noqa: E402
from services.env_setup import deps_manifest  # noqa: E402
from utils.plugin import _manifest  # noqa: E402

# 表外插件多写两个本体不认的键，读取侧按未知键忽略
_MANIFEST = """
name = "{name}"
title = "{name}"
summary = "外部插件"
always = true
weight = 0
deps = []
assets = []
"""


def _write(root: Path, name: str) -> None:
    """在目录下造一份多写键的清单"""
    target = root / name / "plugin.toml"
    target.parent.mkdir(parents=True)
    target.write_text(_MANIFEST.format(name=name), encoding="utf-8")


class TestEnabledOrder(unittest.TestCase):
    """运行期读取：随包表定恒启用与档位"""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        for name in ("extra", "help", "AI"):
            _write(self.root, name)
        patcher = patch.object(
            _manifest, "_plugins_roots", lambda: [(self.root, "bundled")]
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_only_bundled_enabled_without_state(self) -> None:
        """清单自称恒启用不算数，未勾选就不启用"""
        picked = _manifest.enabled_manifests(self.root / "plugins.toml")

        self.assertEqual([m.name for m in picked], ["help", "AI"])

    def test_unknown_keys_not_loaded(self) -> None:
        """读回来的清单对象上没有那两个键"""
        picked = _manifest.enabled_manifests(self.root / "plugins.toml")

        self.assertFalse(hasattr(picked[0], "always"))
        self.assertFalse(hasattr(picked[0], "weight"))

    def test_external_between_bundled(self) -> None:
        """表外插件一律常规档，排在最先档之后最后档之前"""
        state = self.root / "plugins.toml"
        state.write_text('enabled = ["extra"]\n', encoding="utf-8")

        picked = _manifest.enabled_manifests(state)

        self.assertEqual([m.name for m in picked], ["help", "extra", "AI"])


class TestGuideRead(unittest.TestCase):
    """引导期精简实现：多写的键同样不认"""

    def test_unknown_keys_dropped_and_table_orders(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("extra", "help", "AI"):
                _write(root, name)

            rows = deps_manifest.load_manifests([root])

            self.assertEqual([row["name"] for row in rows], ["help", "AI", "extra"])
            self.assertFalse({"always", "weight"} & set(rows[0]))

    def test_bundled_grouped_before_external(self) -> None:
        """随包表里的三只成组在前，表外的名字再靠前也不插进来"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("aardvark", "help", "grant", "AI"):
                _write(root, name)

            rows = deps_manifest.load_manifests([root])

            self.assertEqual(
                [row["name"] for row in rows], ["help", "grant", "AI", "aardvark"]
            )


class TestGuideRoots(unittest.TestCase):
    """引导期根表：仓内在前，外部目录按项目根拼"""

    def test_installed_dir_enters_roots_when_present(self) -> None:
        """外部目录存在才进根表

        - 这条红了说明面板与装库看不到外部插件，或空目录也进了表
        """
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            installed = base / INSTALLED_PLUGINS_NAME

            with patch.object(deps_manifest, "ROOT_DIR", base):
                names = [path.name for path in deps_manifest.plugins_roots()]
                self.assertEqual(names, [PLUGINS_PKG])

                installed.mkdir()
                names = [path.name for path in deps_manifest.plugins_roots()]

            self.assertEqual(names, [PLUGINS_PKG, INSTALLED_PLUGINS_NAME])

    def test_bundled_row_wins_same_name(self) -> None:
        """两根目录同名时精简清单只留仓内那一行

        - 这条红了说明外部同名插件会顶掉随包件的那一行
        """
        with tempfile.TemporaryDirectory() as tmp:
            bundled = Path(tmp) / PLUGINS_PKG
            installed = Path(tmp) / INSTALLED_PLUGINS_NAME
            for root, title in ((bundled, "仓内"), (installed, "外部")):
                target = root / "dup" / "plugin.toml"
                target.parent.mkdir(parents=True)
                target.write_text(
                    f'name = "dup"\ntitle = "{title}"\nsummary = "同名"\n',
                    encoding="utf-8",
                )

            rows = deps_manifest.load_manifests([bundled, installed])

            self.assertEqual([row["title"] for row in rows], ["仓内"])


if __name__ == "__main__":
    unittest.main()
