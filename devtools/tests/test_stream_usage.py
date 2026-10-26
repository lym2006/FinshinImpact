# devtools/tests/test_stream_usage.py
"""流式用量回读测试

- 末帧带的输入 token 读数写进读数容器
- 末帧不带读数即保持空值
- 读数帧不产出正文，正文帧照常拼全
- 端点读数与字符估并排记一行，没读数即不记
"""

import asyncio
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from core.domain.ids import SessionKey  # noqa: E402
from plugins.AI.core import _client  # noqa: E402
from plugins.AI.core._client import AIClient, StreamUsage  # noqa: E402
from plugins.AI.services import worker  # noqa: E402

_TURN = [{"role": "user", "content": "说一句"}]


def _sse(frames: list[dict[str, Any]]) -> list[str]:
    """把响应帧拼成 SSE 行"""
    lines = [f"data: {json.dumps(frame, ensure_ascii=False)}" for frame in frames]
    return lines + ["data: [DONE]"]


def _lines(lines: list[str]) -> object:
    """交出按行吐出 SSE 的流式替身"""

    async def _fake(*_args: object, **_kwargs: object):
        for line in lines:
            yield line

    return _fake


def _delta(text: str) -> dict[str, Any]:
    """构造一帧正文"""
    return {"choices": [{"delta": {"content": text}}]}


def _config() -> SimpleNamespace:
    """交出客户端组装请求体与鉴权头读到的那组配置"""
    return SimpleNamespace(
        model_name="模型",
        temperature=0.5,
        think_mode=(),
        base_url="https://example.test/v1",
        request_path="/chat/completions",
        timeout=5.0,
        api_key="密钥串",
    )


async def _stream_text(lines: list[str], usage: StreamUsage) -> str:
    """按给定的 SSE 行跑一遍流式请求，交出拼全的正文"""
    parts: list[str] = []
    with (
        patch.object(_client, "ai_config", _config()),
        patch.object(_client.BaseClient, "stream_post", _lines(lines)),
    ):
        async for delta in AIClient.stream_chat(_TURN, usage):
            parts.append(delta.get("content", ""))
    return "".join(parts)


async def _collect_with_reading(
    reading: int | None,
) -> tuple[str, bool, list[str]]:
    """按给定的端点读数收全一轮应答，连同记下的日志一起交出"""
    logged: list[str] = []

    async def _fake_stream(_msg: object, sink: StreamUsage):
        sink.prompt_tokens = reading
        yield {"content": "回话"}

    with (
        patch.object(worker.AIClient, "stream_chat", _fake_stream),
        patch.object(worker, "_logger", SimpleNamespace(info=logged.append)),
    ):
        final_msg, has_error = await worker._collect_reply(
            _TURN, SessionKey("tg.000000"), 3
        )
    return final_msg, has_error, logged


class TestStreamUsage(unittest.TestCase):
    def test_last_frame_reading_recorded(self) -> None:
        """末帧带回数即填入，不带回数即留空"""
        body = [_delta("你"), _delta("好")]
        cases = [
            (_sse(body), None),
            (_sse([*body, {"choices": [], "usage": {"prompt_tokens": 17}}]), 17),
        ]

        for lines, expected in cases:
            with self.subTest(期望读数=expected):
                usage = StreamUsage()

                self.assertEqual(asyncio.run(_stream_text(lines, usage)), "你好")
                self.assertEqual(usage.prompt_tokens, expected)

    def test_collect_reply_logs_usage_pair(self) -> None:
        """收全一轮应答把估算与端点读数并排记一行，没读数即不记"""
        cases = [(42, ["tg.000000 上下文估算 3，端点报 42"]), (None, [])]

        for reading, expected in cases:
            with self.subTest(端点读数=reading):
                final_msg, has_error, logged = asyncio.run(
                    _collect_with_reading(reading)
                )

                self.assertEqual(final_msg, "回话")
                self.assertFalse(has_error)
                self.assertEqual(logged, expected)


if __name__ == "__main__":
    unittest.main()
