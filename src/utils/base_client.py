# src/utils/base_client.py
"""
通用异步 HTTP 客户端基类

提供：
- 异步 HTTP 客户端生命周期管理
- 通用的 GET/POST 请求封装
- SSE 流式解析
- 自动注入代理
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from httpx import AsyncClient

from .config_loader import CONFIG

logger = logging.getLogger("Bot.Client")


class BaseClient:
    """通用 HTTP 客户端基类，封装底层的请求与连接管理"""

    # ==================== 1. 内部辅助方法 ====================

    @classmethod
    @asynccontextmanager
    async def _create_client(
        cls,
        base_url: str = "",
        headers: dict | None = None,
        timeout: float = 90.0,
        use_proxy: bool = True,
    ) -> AsyncGenerator[AsyncClient, None]:
        """创建异步客户端上下文管理器"""
        # 如果外部没传，就自动使用全局配置的代理
        match use_proxy:
            case True:
                proxy = CONFIG["network"]["proxy"]
            case False:
                proxy = None
        client = AsyncClient(
            base_url=base_url, headers=headers, timeout=timeout, proxy=proxy
        )
        try:
            yield client
        finally:
            await client.aclose()

    # ==================== 2. 通用请求方法 ====================

    @classmethod
    async def stream_post(
        cls,
        base_url: str = "",
        request_path: str = "",
        headers: dict | None = None,
        payload: Any = None,
        use_proxy: bool = True,
    ) -> AsyncGenerator[str, None]:
        """通用的流式 POST 请求"""
        async with cls._create_client(
            base_url=base_url, headers=headers, use_proxy=use_proxy
        ) as client:
            async with client.stream("POST", request_path, json=payload) as response:
                if (code := response.status_code) != 200:
                    try:
                        error_body = await response.aread()
                        error_text = error_body.decode("utf-8", errors="ignore")
                    except Exception:
                        error_text = "无法读取错误响应体"

                    raise RuntimeError(f"API 请求失败 [{code}]: {error_text}")

                async for chunk in response.aiter_lines():
                    if chunk is not None:
                        yield chunk

    @classmethod
    async def get_json(
        cls,
        base_url: str = "",
        request_path: str = "",
        headers: dict | None = None,
        use_proxy: bool = True,
    ) -> dict:
        """通用的 GET 请求并返回 JSON"""
        async with cls._create_client(
            base_url=base_url, headers=headers, use_proxy=use_proxy
        ) as client:
            response = await client.get(request_path)
            if response.status_code != 200:
                raise RuntimeError(
                    f"API 请求失败 [{response.status_code}]: {response.text}"
                )
            return response.json()

    @classmethod
    async def get_text(
        cls,
        base_url: str,
        request_path: str = "",
        headers: dict | None = None,
        use_proxy: bool = True,
    ) -> str:
        """通用的 GET 请求并返回原始响应文本"""
        async with cls._create_client(
            base_url=base_url, headers=headers, use_proxy=use_proxy
        ) as client:
            response = await client.get(request_path)
            response.raise_for_status()
            return response.text
