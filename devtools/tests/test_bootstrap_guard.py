# devtools/tests/test_bootstrap_guard.py
"""引导层最后兜底的单元测试

- 引导段炸掉时弹原生弹窗，退出码记 1
- 弹窗正文带类名与消息那一行，调用链不上屏
- 引导段正常返回时不碰弹窗
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


if __name__ == "__main__":
    unittest.main()
