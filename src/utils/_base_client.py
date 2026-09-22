# src/utils/_base_client.py
"""HTTP 基类客户端（内部实现）

- 定义会话生命周期与 GET/POST 封装
- 实现 SSE 解析与代理注入
"""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any, Literal

import httpx

from exceptions import ConnectionFailedError, HTTPStatusError, RequestTimeoutError

# 无配置场景（如版本检查跑在配置加载前）的兜底超时
_DEFAULT_TIMEOUT = 90.0
_CONNECT_TIMEOUT = 10.0


class BaseClient:
    """通用 HTTP 客户端基类"""

    # ==================== 内部辅助方法 ====================

    @classmethod
    @asynccontextmanager
    async def _create_client(
        cls,
        base_url: str = "",
        headers: dict[str, Any] | None = None,
        proxy: str | None = None,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> AsyncGenerator[httpx.AsyncClient, None]:
        """创建异步客户端上下文管理器"""
        timeout_config = httpx.Timeout(
            connect=_CONNECT_TIMEOUT,
            read=timeout,
            write=timeout,
            pool=timeout,
        )

        client = httpx.AsyncClient(
            base_url=base_url, headers=headers, timeout=timeout_config, proxy=proxy
        )
        try:
            yield client
        finally:
            await client.aclose()

    @staticmethod
    def _deal_with_exception(
        response: httpx.Response, method: Literal["POST", "GET"]
    ) -> None:
        """翻译响应异常"""
        try:
            response.raise_for_status()
        except httpx.TimeoutException as e:
            raise RequestTimeoutError() from e
        except httpx.ConnectError as e:
            raise ConnectionFailedError() from e
        except httpx.HTTPStatusError as e:
            raise HTTPStatusError(e.response.status_code, e.response.text) from e

    # ==================== 通用请求方法 ====================

    @classmethod
    async def stream_post(
        cls,
        base_url: str = "",
        request_path: str = "",
        headers: dict[str, Any] | None = None,
        payload: Any = None,
        proxy: str | None = None,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> AsyncGenerator[str, None]:
        """通用的流式 POST 请求"""
        async with cls._create_client(
            base_url=base_url, headers=headers, proxy=proxy, timeout=timeout
        ) as client:
            async with client.stream("POST", request_path, json=payload) as response:
                cls._deal_with_exception(response, "POST")

                async for chunk in response.aiter_lines():
                    if chunk is not None:
                        yield chunk

    @classmethod
    async def get_content(
        cls,
        method: Literal["json", "text"],
        base_url: str = "",
        request_path: str = "",
        headers: dict[str, Any] | None = None,
        proxy: str | None = None,
        max_retries: int = 3,  # 最多重试次数
        retry_delay: float = 1.0,  # 重试间隔时间（单位：秒）
    ) -> dict[str, Any] | str | None:
        """发起 GET 请求"""
        for attempt in range(1, max_retries + 1):
            try:
                async with cls._create_client(
                    base_url=base_url, headers=headers, proxy=proxy
                ) as client:
                    response = await client.get(request_path)
                    cls._deal_with_exception(response, "GET")
                    match method:
                        case "json":
                            return response.json()
                        case "text":
                            return response.text

            except (ConnectionFailedError, RequestTimeoutError):
                # 对网络异常（连接失败、超时）进行重试
                if attempt < max_retries:
                    await asyncio.sleep(retry_delay * attempt)  # 递增延迟
                    continue  # 重试
                else:
                    raise  # 耗尽次数

            except HTTPStatusError:
                # HTTP 状态码错误不重试
                raise
