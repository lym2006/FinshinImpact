# src/utils/safe_session.py
"""
安全网络会话组件

提供：
- 支持代理且自动禁用 SSL 验证的 Aiohttp 会话
- 解决 Bot 启动时 Clash 代理导致的 SSL 握手失败问题
"""

from aiogram.client.session.aiohttp import AiohttpSession


class SafeSession(AiohttpSession):
    """支持代理且自动禁用 SSL 验证的安全网络会话

    用于解决 Bot 启动时 clash 代理导致的 SSL 握手失败问题
    """

    def __init__(self, proxy: str | None = None, **kwargs) -> None:
        super().__init__(proxy=proxy, **kwargs)
        self._connector_init["ssl"] = False
