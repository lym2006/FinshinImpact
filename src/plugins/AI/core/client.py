# src/plugins/AI/core/client.py
"""
AI 核心网络客户端

继承自 BaseClient，封装 AI 专属的鉴权 Headers
"""

import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

from utils import BaseClient

from .config import API_KEY, MODEL_NAME, TEMPERATURE

logger = logging.getLogger("Bot.Plugins.AI.Client")


class AIClient(BaseClient):
    """AI 客户端，自动注入鉴权 Headers 并强制禁用代理"""

    # ==================== 1. 动态生成鉴权 Headers ====================
    @classmethod
    def _headers(cls) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        }

    # ==================== 2. AI 请求方法 ====================

    @classmethod
    async def stream_chat(
        cls,
        msg: list[dict[str, str]] | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """AI 流式聊天请求

        复用 BaseClient 的客户端创建 / 超时 / 错误处理，
        注入鉴权 Headers，禁用代理，
        自身只负责 SiliconFlow SSE 协议的 delta 解析。

        Yields:
            dict: delta 对象，可能包含 "content" 、"reasoning_content"
        """
        payload = {
            "model": MODEL_NAME,
            "messages": msg,
            "stream": True,
            "temperature": TEMPERATURE,
        }

        async for line in super().stream_post(
            base_url="https://api.siliconflow.cn/v1",
            request_path="/chat/completions",
            headers=cls._headers(),
            payload=payload,
            use_proxy=False,
        ):
            if line.startswith("data: "):
                try:
                    data = json.loads(line[6:])
                    delta = data["choices"][0]["delta"]
                    yield delta
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue
