"""连接性异常文案表

- 键是那族异常类本身，定义在接口包
"""

from finshin_sdk.exceptions import (
    DirectTimeoutError,
    ProbeCrashedError,
    ProbeTimeoutError,
    ProxyAddressError,
    ProxyConnectionRefusedError,
    ProxyError,
    ProxySchemeError,
    ProxySchemeMissingError,
    ProxyTimeoutError,
    TelegramServerError,
    TokenError,
    TokenFormatError,
)

CONNECTIVITY_MAP = {
    TokenError: "Token 无效",
    TokenFormatError: "Token 格式错误（应为 数字:密钥）",
    ProbeTimeoutError: "验证超时，请稍后重试",
    ProbeCrashedError: "检查异常，详情见日志",
    TelegramServerError: "无法连接到服务器",
    DirectTimeoutError: "直连超时，请开启系统代理或在代理项填写地址",
    ProxyError: "代理地址有问题：{proxy}",
    ProxySchemeError: "代理协议不支持: {scheme}",
    ProxySchemeMissingError: "代理地址缺少 :// 协议头，收到的是 {proxy}",
    ProxyAddressError: "代理地址格式无法解析: {proxy}",
    ProxyConnectionRefusedError: "无法连接到代理服务器 {proxy}，请检查代理工具是否开启",
    ProxyTimeoutError: "连接代理 {proxy} 超时，请检查网络环境",
}
