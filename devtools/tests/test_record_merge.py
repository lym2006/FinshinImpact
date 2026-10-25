# devtools/tests/test_record_merge.py
"""落盘记录合并测试

- 同群两名成员写进同一份文件
- 条目内注明发言人，引用块不落盘
- 私聊按会话独有一份
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from core.domain import ChatScope, Platform  # noqa: E402
from core.domain.ids import ContainerKey, MessageId, UserId  # noqa: E402
from core.dto import (  # noqa: E402
    ContentDTO,
    InboundEventDTO,
    MsgReferenceDTO,
    PrincipalDTO,
)
from plugins.AI.services import worker  # noqa: E402
from plugins.AI.utils import make_session_key  # noqa: E402


def _event(user: str, name: str, text: str, scope: ChatScope) -> InboundEventDTO:
    """构造一条带引用的入站事件"""
    container = ContainerKey("g100123" if scope == ChatScope.GROUP else f"u{user}")
    principal = PrincipalDTO(
        platform=Platform.TELEGRAM, container=container, user=UserId(user)
    )
    ref = MsgReferenceDTO(
        platform=Platform.TELEGRAM, container=container, message_id=MessageId("7")
    )
    return InboundEventDTO(
        ref=ref,
        principal=principal,
        content=ContentDTO(text=text),
        scope=scope,
        display_name=name,
        reply_text="昨天那句",
        reply_sender_id="999",
        reply_sender_name="王五",
    )


def _write(event: InboundEventDTO, reply: str) -> None:
    worker._save_conversation_record(make_session_key(event.principal), event, reply)


class TestRecordMerge(unittest.TestCase):
    def test_group_members_share_one_file(self) -> None:
        """同群两名成员落到同一份记录"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(worker.ai_config, "record_dir", root):
                _write(_event("111", "张三", "我是张三", ChatScope.GROUP), "张三你好")
                _write(_event("222", "李四", "我是李四", ChatScope.GROUP), "李四你好")

            self.assertEqual([p.name for p in root.iterdir()], ["tg.g100123.md"])
            body = (root / "tg.g100123.md").read_text(encoding="utf8")
            self.assertIn("[张三 | 111]：我是张三", body)
            self.assertIn("[李四 | 222]：我是李四", body)
            self.assertNotIn("引用", body)

    def test_private_chat_keeps_own_file(self) -> None:
        """私聊记录按会话单独成份"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(worker.ai_config, "record_dir", root):
                _write(_event("456", "张三", "私聊一句", ChatScope.PRIVATE), "收到")

            self.assertEqual([p.name for p in root.iterdir()], ["tg.u456.md"])
            body = (root / "tg.u456.md").read_text(encoding="utf8")
            self.assertIn("[456]：私聊一句", body)

    def test_blank_name_falls_back_to_id(self) -> None:
        """显示名缺位时标注用 id 段填"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(worker.ai_config, "record_dir", root):
                _write(_event("333", "", "无名发言", ChatScope.GROUP), "收到")

            body = (root / "tg.g100123.md").read_text(encoding="utf8")
            self.assertIn("[333 | 333]：无名发言", body)


if __name__ == "__main__":
    unittest.main()
