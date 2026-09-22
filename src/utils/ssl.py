# src/utils/ssl.py
"""SSL 会话（内部实现）

- 提供代理兼容且免验证的会话
- 实现 Clash 代理握手兼容
"""

from aiogram.client.session.aiohttp import AiohttpSession


class SSLUnverifiedSession(AiohttpSession):
    """代理免验证会话

    禁 SSL 校验，仅限受信任代理环境。
    """

    def __init__(
        self, proxy: str | None = None, verify: bool = False, **kwargs
    ) -> None:
        # 空串归一为 None：TUN/直连场景 proxy 留空时必须真·不走代理
        super().__init__(proxy=proxy or None, **kwargs)
        self._connector_init["ssl"] = verify
