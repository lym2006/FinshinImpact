# devtools/tests/test_summary_compress.py
"""摘要压缩测试

- 超线当轮裁窗并投递后台压缩
- 未超线不裁窗也不投递
- 压缩正文写回会话，空返回与报错都不落笔
- 摘要超硬上限按句子边界裁尾
"""

import asyncio
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from core.domain import ChatRole, ChatScope, Platform  # noqa: E402
from core.domain.ids import ContainerKey, MessageId, SessionKey, UserId  # noqa: E402
from core.dto import (  # noqa: E402
    ContentDTO,
    InboundEventDTO,
    MessageDTO,
    MsgReferenceDTO,
    PrincipalDTO,
)
from plugins.AI.services import _summary, worker  # noqa: E402

_PERSONA = "人设正文"
_KEY = SessionKey("tg.g100123")


def _rows(count: int) -> tuple[MessageDTO, ...]:
    """构造带人设首行的 count 轮问答"""
    rows = [MessageDTO(role=ChatRole.SYSTEM, content=_PERSONA)]
    for index in range(count):
        rows.append(
            MessageDTO(
                role=ChatRole.USER,
                content=f"这是一句需要占位的问题{index}",
                sender_id=f"{100 + index}",
                sender_name=f"人名{index}",
            )
        )
        rows.append(
            MessageDTO(role=ChatRole.ASSISTANT, content=f"这是一段较长的回答{index}")
        )
    return tuple(rows)


def _event() -> InboundEventDTO:
    """构造一条群消息事件"""
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
        content=ContentDTO(text="最新的一句问话"),
        scope=ChatScope.GROUP,
        display_name="人名9",
    )


class _Ctx:
    """只带事件与应答出口的假上下文"""

    def __init__(self, event: InboundEventDTO) -> None:
        self.event = event
        self.replied: list[str] = []
        self.interaction = SimpleNamespace(probe_existence=self._probe)

    async def _probe(self, ref: object) -> bool:
        return True

    async def reply(self, text: str) -> None:
        self.replied.append(text)


def _stream(*texts: str) -> object:
    """交出按块吐出正文的流式替身"""

    async def _fake(msg: object, usage: object = None):
        for text in texts:
            yield {"content": text}

    return _fake


def _summary_config(soft: int = 512, hard: int = 1024) -> SimpleNamespace:
    """交出压缩协程读到的那组配置"""
    return SimpleNamespace(summary_soft_limit=soft, summary_hard_limit=hard)


def _value(result: object) -> object:
    """交出恒返同一结果的异步替身"""

    async def _call(*args: object, **kwargs: object) -> object:
        return result

    return _call


def _worker_config(trigger: int) -> SimpleNamespace:
    """交出工作循环读到的那组配置"""
    return SimpleNamespace(
        init=({"role": "system", "content": _PERSONA},),
        summary_trigger_tokens=trigger,
        summary_keep_rounds=6,
    )


def _capture(bucket: list) -> object:
    """交出把入参收进桶里的异步替身"""

    async def _call(*args: object) -> None:
        bucket.append(args)

    return _call


def _run_worker(history: tuple[MessageDTO, ...], *, trigger: int):
    """走过一轮工作循环并交出落库窗口与压缩入参"""
    ctx = _Ctx(_event())
    saved: list[tuple[SessionKey, tuple[MessageDTO, ...]]] = []
    compressed: list[tuple[SessionKey, tuple[MessageDTO, ...]]] = []

    async def _fake_compress(key, rows) -> None:
        compressed.append((key, rows))

    async def _drive() -> None:
        snapshot = SimpleNamespace(messages=history, summary="")
        with (
            patch.object(worker, "purge_stale", _value(snapshot)),
            patch.object(worker, "ai_config", _worker_config(trigger)),
            patch.object(worker.AIClient, "stream_chat", _stream("回话")),
            patch.object(worker, "save_session", _capture(saved)),
            patch.object(worker, "compress_history", _fake_compress),
            patch.object(worker, "_save_conversation_record", lambda *a: None),
        ):
            await worker.worker_loop(ctx)
            await asyncio.sleep(0)
            await asyncio.sleep(0)

    asyncio.run(_drive())
    return saved, compressed


class TestWorkerBudget(unittest.TestCase):
    def test_over_trigger_trims_and_kicks(self) -> None:
        """超线当轮只留保留窗口，被裁问答交后台压缩"""
        keep = worker.ai_config.summary_keep_rounds
        saved, compressed = _run_worker(_rows(8), trigger=1)

        self.assertEqual(len(saved), 1)
        window = saved[0][1]
        self.assertEqual(len(window), 1 + keep * 2 + 2)
        self.assertEqual(window[0].content, _PERSONA)
        self.assertEqual(len(compressed), 1)
        self.assertEqual(compressed[0][0], _KEY)
        self.assertEqual(len(compressed[0][1]), (8 - keep) * 2)

    def test_within_trigger_keeps_window(self) -> None:
        """未超线不裁窗也不投递压缩"""
        history = _rows(3)
        saved, compressed = _run_worker(history, trigger=10_000_000)

        self.assertEqual(len(saved[0][1]), len(history) + 2)
        self.assertEqual(compressed, [])


class TestCompressHistory(unittest.TestCase):
    def test_summary_written(self) -> None:
        """压缩正文整段写回会话"""
        written: list[str] = []

        async def _save(key: SessionKey, text: str) -> bool:
            written.append(text)
            return True

        async def _drive() -> None:
            with (
                patch.object(_summary.AIClient, "stream_chat", _stream("摘要", "正文")),
                patch.object(_summary, "save_summary", _save),
                patch.object(_summary, "ai_config", _summary_config()),
            ):
                await _summary.compress_history(_KEY, _rows(2)[1:])

        asyncio.run(_drive())
        self.assertEqual(written, ["摘要正文"])

    def test_blank_result_not_written(self) -> None:
        """模型回空即保留原摘要"""
        written: list[str] = []

        async def _save(key: SessionKey, text: str) -> bool:
            written.append(text)
            return True

        async def _drive() -> None:
            with (
                patch.object(_summary.AIClient, "stream_chat", _stream("   ")),
                patch.object(_summary, "save_summary", _save),
                patch.object(_summary, "ai_config", _summary_config()),
            ):
                await _summary.compress_history(_KEY, _rows(1)[1:])

        asyncio.run(_drive())
        self.assertEqual(written, [])

    def test_request_failure_swallowed(self) -> None:
        """请求报错只记录，不向调用方抛出"""

        async def _boom(msg: object):
            raise RuntimeError("上游断了")
            yield {}

        async def _drive() -> None:
            with patch.object(_summary.AIClient, "stream_chat", _boom):
                await _summary.compress_history(_KEY, _rows(1)[1:])

        asyncio.run(_drive())

    def test_empty_rows_skips_request(self) -> None:
        """待压段为空即不发请求"""
        called: list[str] = []

        async def _fake(msg: object):
            called.append("请求了")
            yield {"content": ""}

        async def _drive() -> None:
            with patch.object(_summary.AIClient, "stream_chat", _fake):
                await _summary.compress_history(_KEY, ())

        asyncio.run(_drive())
        self.assertEqual(called, [])


class TestTrimSummary(unittest.TestCase):
    def test_cut_on_sentence_boundary(self) -> None:
        """超硬上限按句子结束符裁掉前段留尾部"""
        text = "第一句很长足够占位。" * 60 + "结尾这一句要保住。"

        with patch.object(_summary, "ai_config", _summary_config(hard=60)):
            trimmed = _summary._trim_summary(text)

        self.assertTrue(trimmed.endswith("结尾这一句要保住。"))
        self.assertTrue(trimmed.startswith("第一句"))
        self.assertLessEqual(_summary.estimate_tokens(trimmed), 60)

    def test_no_boundary_falls_back_to_ratio(self) -> None:
        """整段没有句子边界时裁出尾巴不裁空"""
        text = "字" * 400

        with patch.object(_summary, "ai_config", _summary_config(hard=60)):
            trimmed = _summary._trim_summary(text)

        self.assertTrue(0 < len(trimmed) < 400)

    def test_short_summary_untouched(self) -> None:
        """没超线一个字都不动"""
        with patch.object(_summary, "ai_config", _summary_config()):
            self.assertEqual(_summary._trim_summary("短句。"), "短句。")


class TestStoreSummary(unittest.TestCase):
    def test_clear_session_empties_summary(self) -> None:
        """清空会话连摘要一起抹掉"""
        from plugins.AI.core import _store

        patched: list[object] = []

        class _Repo:
            async def apply_patch(self, key: SessionKey, patch: object) -> None:
                patched.append(patch)

        async def _drive() -> None:
            with patch.object(_store, "_repo", _value(_Repo())):
                await _store.clear_session(_KEY)

        asyncio.run(_drive())
        self.assertEqual(patched[0].summary, "")

    def test_save_summary_skips_cleared_session(self) -> None:
        """会话已清即不把摘要回填进去"""
        from plugins.AI.core import _store

        saved: list[str] = []

        class _Repo:
            async def load(self, key: SessionKey) -> object:
                return SimpleNamespace(messages=(), summary="")

            async def apply_patch(self, key: SessionKey, patch: object) -> None:
                saved.append(patch.summary)

        async def _drive() -> None:
            with (
                patch.object(_store, "_repo", _value(_Repo())),
                patch.object(_store, "ai_config", _worker_config(1)),
            ):
                written = await _store.save_summary(_KEY, "一段摘要")

            self.assertFalse(written)

        asyncio.run(_drive())
        self.assertEqual(saved, [])


if __name__ == "__main__":
    unittest.main()
