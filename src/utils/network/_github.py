"""GitHub 取数通道

- 版本页、在线目录、发布接口与发行件下载共用一条通道
- 建连失败或超时等一秒重发一次，两次都坏才上抛
"""

import asyncio
from typing import Any, Literal, cast

from exceptions import ConnectionFailedError, RequestTimeoutError
from system.links import API_BASE_URL, API_USER_AGENT, PAGES_BASE_URL

from ._client import BaseClient

_HEADER = {"User-Agent": API_USER_AGENT}

# 度量档
_CONNECT_TIMEOUT = 2.0  # 对 GitHub 建连超时 2 秒
_RETRY_DELAY = 1.0  # 建连失败或超时后的重发等待秒数


class GitClient(BaseClient):
    """GitHub 侧取数客户端

    - 交出网络异常，兜不兜由调用方判
    """

    @classmethod
    async def get_pages(
        cls, path: str, timeout: float, proxy: str | None = None
    ) -> str:
        """取 Pages 上的一份文本"""
        content = await cls._request("text", PAGES_BASE_URL, path, timeout, proxy)

        return cast(str, content or "")

    @classmethod
    async def get_api(cls, path: str, timeout: float, proxy: str | None = None) -> Any:
        """取 release 接口的一段 JSON"""
        return cast(
            dict[str, Any],
            await cls._request("json", API_BASE_URL, path, timeout, proxy),
        )

    @classmethod
    async def get_file(
        cls, url: str, timeout: float, proxy: str | None = None
    ) -> bytes:
        """按完整地址取一份二进制内容"""
        return cast(bytes, await cls._request("bytes", "", url, timeout, proxy))

    @classmethod
    async def _request(
        cls,
        kind: Literal["json", "text", "bytes"],
        base_url: str,
        path: str,
        timeout: float,
        proxy: str | None,
    ) -> Any:
        """取一份内容，建连失败或超时重发一次"""
        try:
            return await cls._once(kind, base_url, path, timeout, proxy)
        except (ConnectionFailedError, RequestTimeoutError):
            await asyncio.sleep(_RETRY_DELAY)
            return await cls._once(kind, base_url, path, timeout, proxy)

    @classmethod
    async def _once(
        cls,
        kind: Literal["json", "text", "bytes"],
        base_url: str,
        path: str,
        timeout: float,
        proxy: str | None,
    ) -> Any:
        """发一次请求，异常原样上抛"""
        return await cls.get_content(
            method=kind,
            base_url=base_url,
            request_path=path,
            headers=_HEADER,
            proxy=proxy,
            timeout=timeout,
            connect_timeout=_CONNECT_TIMEOUT,
        )
