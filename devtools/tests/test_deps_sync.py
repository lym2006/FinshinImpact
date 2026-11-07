# devtools/tests/test_deps_sync.py
"""依赖同步的单元测试

- 同步先 compile 闭包再 sync，装过的开发工具并入保留清单
- 整批失败即返回保留清单全体，开发模式只回手动命令
"""

import sys
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


if __name__ == "__main__":
    unittest.main()
