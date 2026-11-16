"""弹窗按钮的统一守卫

- 问答与提示的按钮文字只有装配那一处出处
- 源码里再出现 Qt 的默认按钮写法，英文串就回到屏上了
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from skin.messages import DialogMessage  # noqa: E402

SRC_DIR = Path(__file__).resolve().parent.parent.parent / "src"

# 按钮装配的唯一落点，其余模块只准调用它交出的两只函数
_ASSEMBLY = Path("ui") / "_guide" / "_popup.py"

# 会带来英文按钮的 Qt 默认写法
_DEFAULT_SEAMS = (
    "QMessageBox.question",
    "QMessageBox.warning",
    "QMessageBox.information",
    "QMessageBox.about",
    "StandardButton",
)


class TestButtonSource(unittest.TestCase):
    """按钮文字只有一个出处"""

    def test_only_the_assembler_touches_qt_buttons(self) -> None:
        """装配那一处之外，源码里不许出现 Qt 的默认按钮写法"""
        found = [
            f"{path.relative_to(SRC_DIR)}:{number}"
            for path in sorted(SRC_DIR.rglob("*.py"))
            if path.relative_to(SRC_DIR) != _ASSEMBLY
            for number, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), start=1
            )
            if any(seam in line for seam in _DEFAULT_SEAMS)
        ]

        self.assertEqual(found, [])

    def test_the_three_labels_are_pinned(self) -> None:
        """三只按钮的文字钉在弹窗文案表里"""
        self.assertEqual(
            (
                DialogMessage.CONFIRM_YES,
                DialogMessage.CONFIRM_NO,
                DialogMessage.NOTICE_OK,
            ),
            ("是", "否", "知道了"),
        )


if __name__ == "__main__":
    unittest.main()
