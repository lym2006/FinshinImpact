"""网络异常族

- 定义 HTTP 请求细分异常与映射表
- 状态码里认得出原因的补一句，整页响应不进界面
"""

from finshin_sdk.exceptions import BotError


class NetworkError(BotError):
    """网络请求异常基类"""


class RequestTimeoutError(NetworkError):
    """请求超时异常"""


class ConnectionFailedError(NetworkError):
    """连接失败异常"""


# 正文里出现这些字样即按匿名额度用完说
_LIMIT_MARKS = ("rate limit", "abuse detection")

# 认得出原因的那几个状态码
_LIMIT_CODES = (401, 403, 429)

_CAUSE_LIMITED = "（这台机器一小时内问 GitHub 的次数用完了，稍后再试）"
_CAUSE_MISSING = "（GitHub 上没找到那份内容）"


class HTTPStatusError(NetworkError):
    """HTTP 状态码异常

    - cause 交出归类后的那句原因，认不出即空串
    """

    def __init__(self, status_code: int, msg: str) -> None:
        self.status_code = status_code
        self.msg = msg
        self.cause = _cause_of(status_code, msg)
        super().__init__()


def _cause_of(status_code: int, msg: str) -> str:
    """按状态码与正文里的信号归类那一句原因"""
    if status_code == 404:
        return _CAUSE_MISSING
    if status_code in _LIMIT_CODES and any(
        mark in msg.lower() for mark in _LIMIT_MARKS
    ):
        return _CAUSE_LIMITED

    return ""


NETWORK_MAP = {
    RequestTimeoutError: "请求超时",
    ConnectionFailedError: "连接失败",
    HTTPStatusError: "HTTP 状态码：{status_code}{cause}",
}
