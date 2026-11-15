"""卸载发行件的单元测试

- 整批一条命令失败转逐只重试并逐只点名
- 交出去的参数表由子进程实收的 argv 钉住，索引地址不进卸载
"""

import sys
import unittest
from collections.abc import Callable
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from services.env_setup import deps_install as mod  # noqa: E402

_SDK_NAME = "finshin-sdk"
_TG_NAME = "finshin-adapter-tg"


class TestRemoveDistributions(unittest.TestCase):
    """uv 卸载与差集收集"""

    def setUp(self) -> None:
        """准备参数记录仪"""
        self.calls: list[list[str]] = []

    def _once(self, code: int) -> Callable[..., int]:
        """按固定退出码记下每次参数的替身"""

        def fake(
            args: list[str], index_url: str | None = None, on_line: object = None
        ) -> int:
            self.calls.append(list(args))
            return code

        return fake

    def test_batch_command_has_no_index(self) -> None:
        """一条命令带全部名，参数表里不带索引地址"""
        with (
            patch.object(mod, "dev_mode", lambda: False),
            patch.object(mod, "run_uv_once", self._once(0)),
        ):
            self.assertEqual(mod.remove_distributions([_TG_NAME]), [])

        self.assertEqual(len(self.calls), 1)
        argv = self.calls[0]
        self.assertNotIn("--index-url", argv)
        self.assertEqual(argv[:3], ["pip", "uninstall", "--python"])
        self.assertIn(_TG_NAME, argv)

    def test_batch_failure_retries_each(self) -> None:
        """整批失败转逐只重试，重试次数等于点名数"""
        with (
            patch.object(mod, "dev_mode", lambda: False),
            patch.object(mod, "run_uv_once", self._once(1)),
        ):
            notes = mod.remove_distributions([_SDK_NAME, _TG_NAME])

        self.assertEqual(len(self.calls), 3)
        self.assertEqual(len(notes), 2)
        self.assertIn(_SDK_NAME, notes[0])
        self.assertIn(_TG_NAME, notes[1])
        self.assertTrue(all("--index-url" not in argv for argv in self.calls))


if __name__ == "__main__":
    unittest.main()
