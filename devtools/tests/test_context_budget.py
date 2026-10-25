# devtools/tests/test_context_budget.py
"""上下文预算测试

- 字符折算按中文与其余两套系数
- 窗口超线切段问答成对不断
- 压缩文本带上发言人标注
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from core.domain import ChatRole, ChatScope  # noqa: E402
from core.dto import MessageDTO  # noqa: E402
from plugins.AI import utils  # noqa: E402


def _rounds(count: int, text: str = "说一句") -> tuple[MessageDTO, ...]:
    """构造 count 轮问答"""
    rows: list[MessageDTO] = []
    for index in range(count):
        rows.append(
            MessageDTO(
                role=ChatRole.USER,
                content=f"{text}{index}",
                sender_id=f"{100 + index % 2}",
                sender_name=f"人名{index % 2}",
            )
        )
        rows.append(MessageDTO(role=ChatRole.ASSISTANT, content=f"回{index}" * 4))
    return tuple(rows)


class TestTokenEstimate(unittest.TestCase):
    def test_cjk_and_ascii_use_different_rates(self) -> None:
        """中文与英文各按自己的系数折算"""
        self.assertEqual(utils.estimate_tokens("你好世界"), 2)
        self.assertEqual(utils.estimate_tokens("abcdefgh"), 2)

    def test_window_sum_includes_all_parts(self) -> None:
        """窗口估算把人设、摘要与问句一起计入"""
        persona = "人设正文"
        window = (
            MessageDTO(role=ChatRole.SYSTEM, content=persona),
            *_rounds(1),
        )
        only_rows = utils.estimate_window(window, "", "")
        self.assertGreater(only_rows, utils.estimate_window(window[1:], "", ""))
        self.assertGreater(utils.estimate_window(window, "摘要", "新问"), only_rows)


class TestSplitRounds(unittest.TestCase):
    def test_keep_tail_rounds(self) -> None:
        """尾部留满指定轮数，更早的进待压段"""
        head, tail = utils.split_rounds(_rounds(8), 3)
        self.assertEqual(len(head), 10)
        self.assertEqual(len(tail), 6)

    def test_no_split_when_within_keep(self) -> None:
        """轮数不足保留窗口即不切"""
        head, tail = utils.split_rounds(_rounds(2), 6)
        self.assertEqual(head, ())
        self.assertEqual(len(tail), 4)

    def test_head_never_ends_with_question(self) -> None:
        """切点撞上答句时连答句一起进待压段"""
        rows = (*_rounds(2), MessageDTO(role=ChatRole.USER, content="半截问"))
        head, tail = utils.split_rounds(rows, 1)
        self.assertEqual(len(tail), 1)
        self.assertEqual(tail[0].role, ChatRole.USER)
        self.assertEqual(head[-1].role, ChatRole.ASSISTANT)


class TestRenderHistory(unittest.TestCase):
    def test_marks_survive_render(self) -> None:
        """压缩文本逐字保留名称与 id 标注"""
        text = utils.render_history(_rounds(2), ChatScope.GROUP)
        self.assertIn("[人名0 | 100] 说一句0", text)
        self.assertIn("回1回1回1回1", text)

    def test_system_row_skipped(self) -> None:
        """人设行不进压缩文本"""
        window = (MessageDTO(role=ChatRole.SYSTEM, content="人设"), *_rounds(1))
        self.assertNotIn("人设", utils.render_history(window, ChatScope.GROUP))


class TestWindowCap(unittest.TestCase):
    def test_persona_row_kept_and_cap_applied(self) -> None:
        """窗口上限放宽到常量值，人设行始终占首位"""
        history = (MessageDTO(role=ChatRole.SYSTEM, content="人设"), *_rounds(200))
        window = utils.open_window("人设", history)
        self.assertEqual(window[0].content, "人设")
        cap = utils._MAX_CONTEXT_MESSAGES - 1 - utils._ROUND_ROWS
        self.assertLessEqual(len(window) - 1, cap)
        self.assertGreaterEqual(len(window) - 1, cap - 1)
        self.assertEqual((len(window) - 1) % utils._ROUND_ROWS, 0)
        self.assertEqual(window[1].role, ChatRole.USER)


if __name__ == "__main__":
    unittest.main()
