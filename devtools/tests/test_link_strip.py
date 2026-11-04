# devtools/tests/test_link_strip.py
"""交模型前剥网址测试

- 发出去那轮的网址换成占位标记，落盘记录与入库正文留着原文
- 摘要与历史轮同样剥，人设轮不动
- 网址后面的中文与全角标点不吃进占位段
- 不带协议的写法不算网址，照原样交出去
- 期望值写逐字串不引常量，标记被改坏这条用例就红
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from bundled.AI.utils import (  # noqa: E402
    build_turns,
    compose_user_text,
    estimate_window,
)
from core.domain import ChatRole, ChatScope, Platform  # noqa: E402
from core.domain.ids import ContainerKey, MessageId, UserId  # noqa: E402
from core.dto import (  # noqa: E402
    ContentDTO,
    InboundEventDTO,
    MessageDTO,
    MsgReferenceDTO,
    PrincipalDTO,
)


def _event(text: str) -> InboundEventDTO:
    """构造一条群聊入站事件"""
    container = ContainerKey("g100123")
    principal = PrincipalDTO(
        platform=Platform.TELEGRAM, container=container, user=UserId("111")
    )
    ref = MsgReferenceDTO(
        platform=Platform.TELEGRAM, container=container, message_id=MessageId("7")
    )
    return InboundEventDTO(
        ref=ref,
        principal=principal,
        content=ContentDTO(text=text),
        scope=ChatScope.GROUP,
        display_name="张三",
    )


class TestLinkStrip(unittest.TestCase):
    def _turn(self, text: str) -> str:
        """取这一轮发往模型的问句正文"""
        turns = build_turns(persona="人设正文", summary="", history=(), thisinput=text)
        return turns[-1]["content"]

    def test_question_url_becomes_mark(self) -> None:
        """问句里的网址换成占位标记，前后中文留在原位"""
        self.assertEqual(
            self._turn("看看 https://example.com/a?b=1 讲了啥"),
            "看看 [链接] 讲了啥",
        )

    def test_bare_host_stays(self) -> None:
        """不带协议也不以 www 起头的写法不动"""
        self.assertEqual(self._turn("去 example.com 看看"), "去 example.com 看看")

    def test_fullwidth_tail_not_eaten(self) -> None:
        """全角标点与中文不算网址的一部分"""
        self.assertEqual(self._turn("见 www.example.com，就这样"), "见 [链接]，就这样")

    def test_summary_url_stripped(self) -> None:
        """摘要轮的网址换成占位标记，行首标记照旧"""
        turns = build_turns(
            persona="人设正文",
            summary="早前聊到 https://example.com 的事",
            history=(),
            thisinput="一句",
        )
        self.assertEqual(turns[1]["content"], "[历史摘要] 早前聊到 [链接] 的事")

    def test_persona_turn_untouched(self) -> None:
        """人设轮一个字不改"""
        persona = "人设里的 https://example.com 照留"
        turns = build_turns(persona=persona, summary="", history=(), thisinput="一句")
        self.assertEqual(turns[0]["content"], persona)

    def test_history_rows_stripped(self) -> None:
        """历史问句连标注与引用块一起剥，答句原样交回"""
        history = (
            MessageDTO(
                role=ChatRole.USER,
                content="（引用 [王五|999]：https://example.com）正文",
                sender_id="111",
                sender_name="张三",
            ),
            MessageDTO(role=ChatRole.ASSISTANT, content="回一句 https://example.com"),
        )
        turns = build_turns(
            persona="人设正文", summary="", history=history, thisinput="再说一句"
        )
        self.assertEqual(
            turns[1]["content"], "[张三|111]（引用 [王五|999]：[链接]）正文"
        )
        self.assertEqual(turns[2]["content"], "回一句 https://example.com")

    def test_record_line_keeps_source(self) -> None:
        """落盘记录的问句行留着原串"""
        event = _event("看看 https://example.com/a")
        self.assertEqual(
            compose_user_text(event), "[张三|111]看看 https://example.com/a"
        )

    def test_estimate_prices_stripped_text(self) -> None:
        """体量折算按剥完的那份算，长网址不再撑大窗口"""
        window = (MessageDTO(role=ChatRole.SYSTEM, content="人设正文"),)
        long_url = "https://example.com/" + "x" * 400
        gap = estimate_window(window, "", long_url) - estimate_window(
            window, "", "一句"
        )
        self.assertLess(gap, 20)


if __name__ == "__main__":
    unittest.main()
