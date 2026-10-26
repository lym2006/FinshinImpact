# src/plugins/AI/core/_client.py
"""AI 客户端

- 定义鉴权头注入与禁用代理的客户端
"""

import json
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Any

from utils.network import BaseClient

from ..config import ai_config


@dataclass
class StreamUsage:
    """流式请求的 token 读数容器"""

    prompt_tokens: int | None = None


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
        usage: StreamUsage | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """AI 流式聊天请求

        - 解析 SSE delta
        - 交出读数容器即填入端点报的输入 token 数
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

                    # 末帧只带读数不带 choices，取完照旧走异常跳过
                    if usage is not None and (read := data.get("usage")):
                        usage.prompt_tokens = read["prompt_tokens"]

                    delta = data["choices"][0]["delta"]
                    yield delta
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue
