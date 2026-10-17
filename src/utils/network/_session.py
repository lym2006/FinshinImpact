# src/utils/network/_session.py
"""SSL 会话

- 提供代理兼容且免验证的会话
- 实现 Clash 代理握手兼容
- 链路失败与恢复转交链路上报器
"""

import asyncio
from typing import TYPE_CHECKING

import aiohttp
import aiohttp_socks
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.exceptions import TelegramNetworkError
from aiogram.methods.base import TelegramMethod, TelegramType

from ._link import link_report

# 链路层异常族：服务端有回应即不在其内
_LINK_ERRORS: tuple[type[BaseException], ...] = (
    TelegramNetworkError,
    aiohttp.ClientError,
    aiohttp_socks.ProxyError,
    aiohttp_socks.ProxyConnectionError,
    aiohttp_socks.ProxyTimeoutError,
    aiohttp_socks.SocksError,
    aiohttp_socks.SocksConnectionError,
    OSError,
    asyncio.TimeoutError,
)

# 秒，会话级请求超时；请求挂死到此刻才判失败，即断连检测延迟上限
_REQUEST_TIMEOUT = 30.0

if TYPE_CHECKING:
    from aiogram.client.bot import Bot


def is_link_failure(exc: BaseException) -> bool:
    """判定是否链路层失败

    - 服务端有回应的 TelegramAPIError 家族不在其内
    """
    return isinstance(exc, _LINK_ERRORS)


class SSLUnverifiedSession(AiohttpSession):
    """代理免验证会话

    - 禁 SSL 校验，仅限受信任代理环境
    - 链路失败与恢复在此上报，异常类型原样抛出，重试由轮询循环负责
    """

    def __init__(
        self, proxy: str | None = None, verify: bool = False, **kwargs
    ) -> None:
        # 空串归一为 None：TUN/直连场景 proxy 留空时必须真·不走代理
        super().__init__(proxy=proxy or None, timeout=_REQUEST_TIMEOUT, **kwargs)
        self._connector_init["ssl"] = verify

    async def make_request(
        self,
        bot: "Bot",
        method: "TelegramMethod[TelegramType]",
        timeout: int | None = None,
    ) -> TelegramType:
        """发起请求并上报链路状态"""
        try:
            result = await super().make_request(bot, method, timeout=timeout)
        except Exception as exc:
            if is_link_failure(exc):
                link_report.failed(type(method).__name__, exc)
            raise
        link_report.recovered()
        return result
