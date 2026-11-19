"""HTTP 基类客户端

- 会话生命周期与 GET/POST 封装
- SSE 解析与代理注入
- 代理只由参数注入，环境里的代理表不参与
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any, Literal

import httpx

from exceptions import ConnectionFailedError, HTTPStatusError, RequestTimeoutError

# 请求默认超时：读、写与连接池三档共用
_DEFAULT_TIMEOUT = 90.0
_CONNECT_TIMEOUT = 10.0


class BaseClient:
    """通用 HTTP 客户端基类"""

    @classmethod
    @asynccontextmanager
    async def _create_client(
        cls,
        base_url: str = "",
        headers: dict[str, Any] | None = None,
        proxy: str | None = None,
        timeout: float = _DEFAULT_TIMEOUT,
        connect_timeout: float = _CONNECT_TIMEOUT,
    ) -> AsyncGenerator[httpx.AsyncClient, None]:
        """创建异步客户端上下文管理器"""
        timeout_config = httpx.Timeout(
            connect=connect_timeout,
            read=timeout,
            write=timeout,
            pool=timeout,
        )

        client = httpx.AsyncClient(
            base_url=base_url,
            headers=headers,
            timeout=timeout_config,
            proxy=proxy,
            # 代理只由参数注入，环境里的代理表与 NO_PROXY 不参与建客户端
            trust_env=False,
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
        """流式 POST 请求"""
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
        method: Literal["json", "text", "bytes"],
        base_url: str = "",
        request_path: str = "",
        headers: dict[str, Any] | None = None,
        proxy: str | None = None,
        timeout: float = _DEFAULT_TIMEOUT,
        connect_timeout: float = _CONNECT_TIMEOUT,
    ) -> dict[str, Any] | str | bytes | None:
        """GET 请求

        - 网络与状态码异常各自转成本体异常上抛
        """
        async with cls._create_client(
            base_url=base_url,
            headers=headers,
            proxy=proxy,
            timeout=timeout,
            connect_timeout=connect_timeout,
        ) as client:
            response = await client.get(request_path)
            cls._deal_with_exception(response, "GET")
            if method == "json":
                return response.json()
            if method == "bytes":
                return response.content
            return response.text
