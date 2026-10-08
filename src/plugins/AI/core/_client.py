# src/plugins/AI/core/_client.py
"""AI 客户端

- 定义鉴权头注入与禁用代理的客户端
"""

import json
from collections.abc import AsyncGenerator
from typing import Any

from utils.base_client import BaseClient

from ..config import ai_config


class AIClient(BaseClient):
    """鉴权与禁代理客户端"""

    @classmethod
    def _headers(cls) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {ai_config.api_key}",
            "Content-Type": "application/json",
        }

    @classmethod
    async def stream_chat(
        cls,
        msg: list[dict[str, str]] | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """AI 流式聊天请求

        - 复用 BaseClient 超时与错误处理
        - 解析 SSE delta
        """
        payload = {
            "model": ai_config.model_name,
            "messages": msg,
            "stream": True,
            "temperature": ai_config.temperature,
            **dict(ai_config.think_mode),
        }

        async for line in super().stream_post(
            base_url=ai_config.base_url,
            request_path=ai_config.request_path,
            headers=cls._headers(),
            payload=payload,
            timeout=ai_config.timeout,
        ):
            if line.startswith("data: "):
                try:
                    data = json.loads(line[6:])
                    delta = data["choices"][0]["delta"]
                    yield delta
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue
