# src/exceptions/_connectivity.py
"""连接性异常族（内部实现）

- 定义代理与 Token 探测的细分异常
"""

from ._base import BotError


class ConnectivityError(BotError):
    """连接性异常基类"""


class TelegramServerError(ConnectivityError):
    """Telegram 服务器异常"""


class DirectTimeoutError(ConnectivityError):
    """无代理直连超时"""


class TokenError(ConnectivityError):
    """Token 异常"""


class ProxyError(ConnectivityError):
    """代理异常基类"""

    def __init__(self, proxy: str) -> None:
        self.proxy = proxy
        super().__init__()


class ProxySchemeError(ProxyError):
    """代理协议头错误"""

    def __init__(self, scheme: str = "未知协议", proxy: str = "") -> None:
        self.scheme = scheme
        super().__init__(proxy)


class ProxyAddressError(ProxyError):
    """代理地址解析错误"""


class ProxyConnectionRefusedError(ProxyError):
    """代理连接被拒绝"""


class ProxyTimeoutError(ProxyError):
    """代理连接超时"""


CONNECTIVITY_MAP = {
    TokenError: "Token 无效",
    TelegramServerError: "无法连接到服务器",
    DirectTimeoutError: "直连超时，请开启系统代理或在代理项填写地址",
    "Proxy": {
        ProxySchemeError: "代理协议不支持: {scheme}",
        ProxyAddressError: "代理地址格式无法解析: {proxy}",
        ProxyConnectionRefusedError: "无法连接到代理服务器 {proxy}，请检查代理工具是否开启",
        ProxyTimeoutError: "连接代理 {proxy} 超时，请检查网络环境",
    },
}
