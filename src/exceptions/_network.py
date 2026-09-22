# src/exceptions/_network.py
"""网络异常族（内部实现）

- 定义 HTTP 请求细分异常与映射表
"""

from ._base import BotError


class NetworkError(BotError):
    """网络请求异常基类"""


class RequestTimeoutError(NetworkError):
    """请求超时异常"""


class ConnectionFailedError(NetworkError):
    """连接失败异常"""


class HTTPStatusError(NetworkError):
    """HTTP 状态码异常"""

    def __init__(self, status_code: int, msg: str) -> None:
        self.status_code = status_code
        self.msg = msg
        super().__init__()


NETWORK_MAP = {
    RequestTimeoutError: "请求超时",
    ConnectionFailedError: "连接失败",
    HTTPStatusError: "\nHTTP 状态码：{status_code}\n错误信息：{msg}",
}
