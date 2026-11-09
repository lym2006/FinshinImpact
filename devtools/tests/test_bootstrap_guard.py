# devtools/tests/test_bootstrap_guard.py
"""引导层最后兜底的单元测试

- 引导段炸掉时弹原生弹窗，退出码记 1
- 弹窗正文只带异常类名，异常原文不上屏
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


class BootstrapGuardCase(unittest.TestCase):
    """main() 那层 try 的取舍"""

    def test_guide_crash_pops_native_notice(self) -> None:
        """引导段抛出的异常走原生弹窗，程序按失败退出

        - 这一步日志器还没挂上，屏幕上那句是唯一出口
        """
        popped: list[tuple[str, str]] = []

        def break_out() -> int:
            raise RuntimeError("缺的是界面库这件事不许上屏")

        with (
            patch.object(slot, "_guide", break_out),
            patch.object(
                slot, "show_error", lambda title, body: popped.append((title, body))
            ),
        ):
            self.assertEqual(slot.main(), 1)

        self.assertEqual(len(popped), 1)
        self.assertIn("RuntimeError", popped[0][1])
        self.assertNotIn("缺的是界面库这件事不许上屏", popped[0][1])

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
