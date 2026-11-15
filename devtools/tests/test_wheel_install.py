"""wheel 装机的单元测试

- 版本对不上才装，相等即跳过
- 一条命令带全部件与 --find-links，参数紧跟子命令名
- 整批失败转逐只重试并逐只点名
- 开发模式只交等效手动命令，不动环境
"""

import sys
import unittest
from collections.abc import Callable
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from services.env_setup import wheel_install as mod  # noqa: E402

_SDK_NAME = "finshin-sdk"
_TG_NAME = "finshin-adapter-tg"


def _file(distribution: str, stem: str) -> mod.WheelFile:
    """拼一只落在 wheel 目录里的件"""
    return mod.WheelFile(
        distribution=distribution,
        path=Path("wheels") / f"{stem}-0.1.0-py3-none-any.whl",
    )


def _files() -> list[mod.WheelFile]:
    """接口包与适配器各一只件"""
    return [_file(_SDK_NAME, "finshin_sdk"), _file(_TG_NAME, "finshin_adapter_tg")]


class TestInstallReleases(unittest.TestCase):
    """uv 装机与差集收集"""

    def setUp(self) -> None:
        """准备两只件与参数记录仪"""
        self.calls: list[list[str]] = []

    def _retry(self, code: int) -> Callable[..., int]:
        """按固定退出码记下每次参数的替身"""

        def fake(args: list[str], on_line: object = None) -> int:
            self.calls.append(list(args))
            return code

        return fake

    def test_batch_success_needs_no_notes(self) -> None:
        """一条命令带两只件，全成即无说明"""
        with (
            patch.object(mod, "dev_mode", lambda: False),
            patch.object(mod, "with_index_retry", self._retry(0)),
        ):
            notes = mod.install_releases(_files(), None)

        self.assertEqual(notes, [])
        self.assertEqual(len(self.calls), 1)
        argv = self.calls[0]
        self.assertEqual(argv[:2], ["pip", "install"])
        self.assertEqual(argv[2], "--python")
        self.assertEqual(argv[4], "--cache-dir")
        self.assertIn("--find-links", argv)
        self.assertEqual(argv.count("--find-links"), 1)
        self.assertTrue(all(str(item.path) in argv for item in _files()))

    def test_batch_failure_retries_each(self) -> None:
        """整批失败转逐只重试并逐只点名"""
        with (
            patch.object(mod, "dev_mode", lambda: False),
            patch.object(mod, "with_index_retry", self._retry(1)),
        ):
            notes = mod.install_releases(_files(), None)

        self.assertEqual(len(self.calls), 3)
        self.assertEqual(len(notes), 2)
        self.assertIn(_SDK_NAME, notes[0])
        self.assertIn(_TG_NAME, notes[1])
        self.assertIn("装不进运行环境", notes[0])

    def test_dev_mode_only_prints_command(self) -> None:
        """开发模式只交等效手动命令，不跑子进程"""
        lines: list[str] = []

        def collect(text: str) -> None:
            lines.append(text)

        with (
            patch.object(mod, "dev_mode", lambda: True),
            patch.object(mod, "with_index_retry", self._retry(0)),
        ):
            notes = mod.install_releases(_files(), collect)

        self.assertEqual(self.calls, [])
        self.assertEqual(len(notes), 2)
        self.assertTrue(any("uv pip install" in line for line in lines))

    def test_empty_files_do_nothing(self) -> None:
        """没有要装的件即不动"""
        with (
            patch.object(mod, "dev_mode", lambda: False),
            patch.object(mod, "with_index_retry", self._retry(0)),
        ):
            notes = mod.install_releases([], None)

        self.assertEqual(notes, [])
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
