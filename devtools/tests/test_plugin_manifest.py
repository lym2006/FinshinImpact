# devtools/tests/test_plugin_manifest.py
"""插件清单恒启用与档位的单元测试

- 清单只认 name/title/summary/deps/assets/help
- 恒启用与加载档位来自随包表，多写的键按未知键忽略
- 引导期精简实现与运行期读取在这两条上一致
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from services.env_setup import deps_manifest  # noqa: E402
from utils.plugin import _manifest  # noqa: E402

# 外部插件多写两个本体不认的键，读取侧按未知键忽略
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
        patcher = patch.object(_manifest, "_plugins_dir", lambda: self.root)
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

            rows = deps_manifest.load_manifests(root)

            self.assertEqual([row["name"] for row in rows], ["help", "extra", "AI"])
            self.assertFalse({"always", "weight"} & set(rows[0]))


if __name__ == "__main__":
    unittest.main()
