# devtools/tests/test_bootstrap_guard.py
"""引导层最后兜底的单元测试

- 引导段炸掉时弹原生弹窗，退出码记 1
- 弹窗正文带类名与消息那一行，调用链不上屏
- 引导段正常返回时不碰弹窗
- 入口脚本那层兜底：主程序导入之前就炸也弹一句再退出
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SRC_DIR = Path(__file__).resolve().parents[2] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from bootstrap import _slot as slot  # noqa: E402
from system.native_dialog import describe  # noqa: E402
from system.startup_guard import startup_guard  # noqa: E402


class BootstrapGuardCase(unittest.TestCase):
    """main() 那层 try 的取舍"""

    def test_guide_crash_pops_native_notice(self) -> None:
        """引导段抛出的异常走原生弹窗，程序按失败退出

        - 这一步日志器还没挂上，屏幕上那一句是唯一出口
        """
        popped: list[tuple[str, str]] = []

        def break_out() -> int:
            raise ImportError("cannot import name 'show_launch_wait' from 'ui'")

        with (
            patch.object(slot, "_guide", break_out),
            patch.object(
                slot, "show_error", lambda title, body: popped.append((title, body))
            ),
        ):
            self.assertEqual(slot.main(), 1)

        self.assertEqual(len(popped), 1)
        self.assertIn("ImportError: cannot import name", popped[0][1])
        self.assertNotIn("Traceback", popped[0][1])

    def test_long_message_is_cut_to_one_line(self) -> None:
        """消息过长即截断，窗上不致撑成一片

        - 截断只动窗上那份，日志里仍是完整消息
        """
        detail = describe(ValueError("x" * 400))
        self.assertTrue(len(detail) <= 122)
        self.assertTrue(detail.endswith("…"))

    def test_normal_guide_returns_code_untouched(self) -> None:
        """引导段正常返回时不弹窗，退出码原样交出

        - 这条红了说明兜底把正常启动也接走了
        """
        popped: list[tuple[str, str]] = []

        with (
            patch.object(slot, "_guide", lambda: 0),
            patch.object(
                slot, "show_error", lambda title, body: popped.append((title, body))
            ),
        ):
            self.assertEqual(slot.main(), 0)

        self.assertEqual(popped, [])


class EntryGuardCase(unittest.TestCase):
    """发布包 main.py 那层 with 的取舍"""

    def test_import_failure_pops_then_exits(self) -> None:
        """主程序导入之前就炸时弹一句并按失败退出

        - 这一步连日志器都没有，屏上那句是唯一出口
        """
        popped: list[tuple[str, str]] = []

        with (
            patch(
                "system.startup_guard.show_error",
                lambda title, body: popped.append((title, body)),
            ),
            self.assertRaises(SystemExit) as ctx,
            startup_guard(),
        ):
            raise ModuleNotFoundError("No module named 'bootstrap'")

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("程序启动失败，包文件可能不完整", popped[0][1])
        self.assertIn("ModuleNotFoundError", popped[0][1])

    def test_clean_import_passes_through(self) -> None:
        """没炸时这层不拦路，正常走完"""
        popped: list[tuple[str, str]] = []

        with (
            patch(
                "system.startup_guard.show_error",
                lambda title, body: popped.append((title, body)),
            ),
            startup_guard(),
        ):
            marker = 1

        self.assertEqual(marker, 1)
        self.assertEqual(popped, [])


if __name__ == "__main__":
    unittest.main()


class LaunchCardCleanup(unittest.TestCase):
    """提示卡的收口盖到哪一段"""

    def test_import_failure_still_closes_card(self) -> None:
        """导入段炸掉，卡片先收掉再往上抛

        - 留一张计时卡在报错窗后面继续走表，就是要修的形态
        """
        closed: list[int] = []

        class _Card:
            def close(self) -> None:
                closed.append(1)

        def break_imports() -> None:
            raise ImportError("no module named 'bot'")

        with (
            patch.object(slot, "_acquire_slot", lambda: None),
            patch.object(slot, "_handle", lambda _result: None),
            patch.object(slot, "get_profile", lambda: "tg.000000"),
            patch("ui.show_launch_wait", lambda _profile: _Card()),
            patch.object(slot, "_pump_imports", break_imports),
        ):
            with self.assertRaises(ImportError):
                slot._guide()

        self.assertEqual(closed, [1])
