# devtools/tests/test_markdown_clean.py
"""模型应答样式清洗的单元测试

- 成对标记、单星号斜体、行内代码与标题井号只去符号，正文原样留
- 链接留标签文字，图片整段删除
- 围栏代码只丢围栏行，行间正文与换行不动
- 空格隔开的星号不误伤，纯文本过一遍字不变
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from plugins.AI.markdown import strip_model_marks  # noqa: E402


class TestEmphasis(unittest.TestCase):
    """强调与代码标记的剥离"""

    def test_pair_marks_strip_to_text(self) -> None:
        """成对标记只去符号，正文与嵌套一层都收干净"""
        cases = {
            "**重点**句子": "重点句子",
            "***三重叠***": "三重叠",
            "__下划线__": "下划线",
            "~~删除线~~": "删除线",
            "`code`": "code",
            "`` `内层` ``": " 内层 ",
        }
        with self.subTest(cases=cases):
            for raw, expected in cases.items():
                self.assertEqual(strip_model_marks(raw), expected, f"漏洗：{raw}")

    def test_single_asterisk_italic(self) -> None:
        """紧贴单词的单星号斜体照剥"""
        self.assertEqual(strip_model_marks("*斜*体"), "斜体")

    def test_spacing_protects_operators(self) -> None:
        """两侧带空格的星号当乘号用，不许误伤"""
        self.assertEqual(strip_model_marks("a * b * c"), "a * b * c")

    def test_heading_hash_removed(self) -> None:
        """行首井号串连同后随空格去掉"""
        self.assertEqual(strip_model_marks("# 标题\n## 二级"), "标题\n二级")


class TestLinks(unittest.TestCase):
    """链接与图片标记"""

    def test_link_keeps_label(self) -> None:
        """链接只留标签文字，地址丢掉"""
        self.assertEqual(
            strip_model_marks("[标签](https://example.com)"), "标签", "链接没洗成纯文本"
        )

    def test_image_dropped_whole(self) -> None:
        """图片整段删除，不留空标签"""
        self.assertEqual(
            strip_model_marks("看 ![图](https://example.com/a.png) 这张"), "看  这张"
        )


class TestFence(unittest.TestCase):
    """围栏代码块"""

    def test_fence_lines_dropped_body_kept(self) -> None:
        """围栏行连同换行丢弃，行间正文一字不动"""
        cleaned = strip_model_marks("```python\nprint(1)\n```\n收尾")
        self.assertEqual(cleaned, "print(1)\n收尾")

    def test_plain_text_is_idempotent(self) -> None:
        """纯文本过一遍字不变，换行照留"""
        text = "第一行\n第二行 保留空格\n"
        self.assertEqual(strip_model_marks(text), text)


if __name__ == "__main__":
    unittest.main()
