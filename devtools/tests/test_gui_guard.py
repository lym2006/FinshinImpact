# devtools/tests/test_gui_guard.py
"""控制器装饰器兜底的单元测试

- 正常返回原样透传
- 系统级错误由控制器自己那句落日志
- 其余异常交装饰器兜住，日志要点名是哪只控制器
"""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SRC_DIR = Path(__file__).resolve().parents[2] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from ui._windows._controllers import _decorator, _system  # noqa: E402
from ui._windows._controllers._decorator import gui_guard  # noqa: E402


class StubController:
    """只用来验装饰器形状的桩"""

    @gui_guard
    def execute(self, count: int) -> int:
        return count * 2


class TestGuiGuard(unittest.TestCase):
    """回归点

    - 兜住不等于吞掉痕迹：日志要带类名，按钮派发全都叫 execute
    """

    def setUp(self) -> None:
        self.logged: list[tuple[str, BaseException]] = []
        patcher = patch.object(
            _decorator._logger,
            "send_error",
            lambda desc, exc: self.logged.append((desc, exc)),
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_return_passes_through(self) -> None:
        self.assertEqual(StubController().execute(3), 6)
        self.assertEqual(self.logged, [])

    def test_log_names_the_controller(self) -> None:
        """意外异常不外抛，但日志要认得出是谁"""
        self.assertIsNone(StubController().execute(None))  # type: ignore[arg-type]

        self.assertEqual(len(self.logged), 1, "接住的异常必须落一行日志")
        self.assertIn("StubController.execute", self.logged[0][0])

    def test_os_error_stays_with_the_owner(self) -> None:
        """系统级错误仍由日志控制器自己那句报，不外溢也不换文案"""
        ctrl = _system.LogsController(SimpleNamespace())
        owned: list[tuple[str, BaseException]] = []
        with (
            patch.object(ctrl.logger, "send_error", lambda d, e: owned.append((d, e))),
            patch.object(_system, "activate_explorer", side_effect=OSError("被占用")),
        ):
            ctrl.execute()

        self.assertEqual(len(owned), 1, "系统级错误应落控制器自己那一句")
        self.assertEqual(self.logged, [], "控制器已接住的不该再冒到装饰器")

    def test_unknown_error_falls_to_the_guard(self) -> None:
        """非系统级错误交装饰器兜住，GUI 线程不死"""
        ctrl = _system.LogsController(SimpleNamespace())
        owned: list[tuple[str, BaseException]] = []
        with (
            patch.object(ctrl.logger, "send_error", lambda d, e: owned.append((d, e))),
            patch.object(_system, "activate_explorer", side_effect=ValueError("意外")),
        ):
            self.assertIsNone(ctrl.execute())

        self.assertEqual(owned, [], "内层不再重复兜底")
        self.assertEqual(len(self.logged), 1)
        self.assertIn("LogsController.execute", self.logged[0][0])
