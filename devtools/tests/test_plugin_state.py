"""实例插件状态读取的单元测试

- 状态文件不存在交出 None，代表实例从未保存过插件选择
- 文件在但启用键缺失交出空集，与没这份文件分得开
- 启用集里非串的成员按字面值收
- 目录指纹缺失、损坏或整份文件不在都交出空串
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from finshin_sdk.domain import StateKey  # noqa: E402
from system.plugin_state import (  # noqa: E402
    load_instance_catalog,
    load_instance_enabled,
)


class TestPluginState(unittest.TestCase):
    """一份状态文件的两键读法"""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.state = Path(self._tmp.name) / "plugins.toml"

    def _write(self, text: str) -> None:
        """造一份状态文件"""
        self.state.write_text(text, encoding="utf-8")

    def test_missing_file_reads_none(self) -> None:
        """没有状态文件即从没保存过选择，读回的不是空集"""
        self.assertIsNone(load_instance_enabled(self.state, StateKey.ENABLED))

    def test_missing_key_reads_empty_set(self) -> None:
        """文件里没启用那一键时读回空集，与没有文件是两种盘面"""
        self._write('catalog = "dig"\n')

        self.assertEqual(
            load_instance_enabled(self.state, StateKey.ENABLED), frozenset()
        )

    def test_broken_file_reads_none(self) -> None:
        """语法坏的文件读不出，按从没保存过处理"""
        self._write("enabled = [")

        self.assertIsNone(load_instance_enabled(self.state, StateKey.ENABLED))

    def test_names_are_kept_as_text(self) -> None:
        """名单成员一律收成文本，数字与串写成同一种时算同一只插件"""
        self._write('enabled = ["help", 3]\n')

        self.assertEqual(
            load_instance_enabled(self.state, StateKey.ENABLED),
            frozenset({"help", "3"}),
        )

    def test_catalog_absent_variants_read_empty(self) -> None:
        """指纹缺键、文件坏与文件不在都读成空串"""
        for text in (None, "enabled = []\n", "catalog = ["):
            with self.subTest(text=text):
                if text is None:
                    self.state.unlink(missing_ok=True)
                else:
                    self._write(text)

                self.assertEqual(
                    load_instance_catalog(self.state, StateKey.CATALOG), ""
                )

    def test_catalog_reads_the_written_value(self) -> None:
        """盘上写了指纹即原样读出"""
        self._write('catalog = "abc123"\n')

        self.assertEqual(load_instance_catalog(self.state, StateKey.CATALOG), "abc123")


if __name__ == "__main__":
    unittest.main()
