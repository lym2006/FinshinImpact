# src/bot/_managers/_settings/_connectivity.py
"""连接性检查（内部实现）

- 实现代理与 Token 双重探测
- 定义构造期与请求期异常的映射规则
"""

import asyncio
import re

import aiohttp_socks
from aiogram import Bot
from aiogram.exceptions import TelegramNetworkError, TelegramUnauthorizedError
from aiohttp import ClientOSError

from exceptions import (
    ConnectivityError,
    DirectTimeoutError,
    ProxyAddressError,
    ProxyConnectionRefusedError,
    ProxyError,
    ProxySchemeError,
    ProxyTimeoutError,
    TelegramServerError,
    TokenError,
)
from utils.config import PENDING_MARK
from utils.ssl import SSLUnverifiedSession

# 本地超时：防不可达代理挂满系统级 TCP 超时（~21s）
_CONNECT_TIMEOUT = 5.0

# yarl 构造期异常消息 → 配置键的解析规则
_SCHEME_RE = re.compile(r"Invalid scheme component:\s*(.*)", re.IGNORECASE)


def map_construct_error(e: Exception, proxy: str) -> ConnectivityError:
    """映射构造期异常"""
    if isinstance(e, UnicodeError):
        # idna 域名标签非法（如 192..168.1.1）
        return ProxyAddressError(proxy=proxy)

    msg = str(e)
    m = _SCHEME_RE.search(msg)
    if m:
        scheme = m.group(1).strip() or "（空，缺少 :// 协议头）"
        return ProxySchemeError(scheme=scheme, proxy=proxy)

    if "port" in msg.lower():
        return ProxyAddressError(proxy=proxy)

    return ProxyError(proxy=proxy)


def _map_request_error(e: Exception, proxy: str) -> ConnectivityError:
    """映射请求期异常"""
    # 子类分支必须排在父类前
    if isinstance(e, TelegramUnauthorizedError):
        return TokenError()

    if isinstance(e, TelegramNetworkError):
        if not proxy:
            # 无代理的网络错误属于直连不通，与代理无关
            return DirectTimeoutError()
        if isinstance(e.__cause__, ClientOSError):
            return ProxyConnectionRefusedError(proxy=proxy)
        return TelegramServerError()

    if isinstance(e, aiohttp_socks.ProxyTimeoutError):
        return ProxyTimeoutError(proxy=proxy)

    if isinstance(e, (aiohttp_socks.ProxyError, aiohttp_socks.ProxyConnectionError)):
        return ProxyConnectionRefusedError(proxy=proxy)

    return ConnectivityError()


async def probe_proxy(proxy: str) -> None:
    """纯代理探测

    构造期异常须映射为业务异常，防上层误判致命。
    """
    try:
        SSLUnverifiedSession(proxy=proxy)
    except (ValueError, UnicodeError) as e:
        raise map_construct_error(e, proxy) from e


async def get_me(token: str, proxy: str) -> None:
    """探测 Token 有效性

    失败抛 ConnectivityError 族。
    """
    bot: Bot | None = None
    try:
        session = SSLUnverifiedSession(proxy=proxy)
        bot = Bot(token=token, session=session)
        await asyncio.wait_for(bot.get_me(), timeout=_CONNECT_TIMEOUT)
    except TimeoutError as e:
        # 无代理时超时是直连不通，不能报"连接代理超时"的空地址文案
        raise (ProxyTimeoutError(proxy=proxy) if proxy else DirectTimeoutError()) from e
    except (ValueError, UnicodeError) as e:
        # 构造期异常穿透兜底（正常流程已在 probe_proxy 拦截）
        raise map_construct_error(e, proxy) from e
    except Exception as e:
        raise _map_request_error(e, proxy) from e
    finally:
        if bot is not None:
            try:
                await bot.session.close()
            except Exception:
                pass


def _is_token_wellformed(token: str) -> bool:
    """本地校验 Token 结构"""
    return re.fullmatch(r"\d+:[A-Za-z0-9_-]+", token.strip()) is not None


async def check_config(
    token: str,
    proxy: str,
    probe=probe_proxy,
    get_me=get_me,
) -> dict[str, str]:
    """双探测聚合

    proxy 先测，通过后再测 token；proxy 坏时 token 标记"暂未检测"而非"无效"
    """
    errors: dict[str, str] = {}
    proxy_text = ""

    try:
        await probe(proxy)
    except ConnectivityError as e:
        proxy_text = _err_text(e)

    if proxy_text:
        errors["proxy"] = proxy_text
        # 代理坏时请求出不了本机，getMe 结果无意义：标暂未检测而非无效
        errors["telegram_token"] = f"{PENDING_MARK}：代理修复后复查"
        return errors

    if not _is_token_wellformed(token):
        errors["telegram_token"] = "Token 格式错误（应为 数字:密钥）"
        return errors

    try:
        await get_me(token, proxy)
    except TokenError as e:
        errors["telegram_token"] = _err_text(e)
    except ConnectivityError as e:
        # getMe 阶段才暴露的网络问题归到 proxy
        errors["proxy"] = _err_text(e)

    return errors


def _err_text(e: ConnectivityError) -> str:
    """生成可读错误文案"""
    from exceptions import MAPS

    template = MAPS["Connectivity"]["Proxy"].get(type(e)) or MAPS["Connectivity"].get(
        type(e)
    )
    if not template:
        return type(e).__name__
    try:
        return template.format(**vars(e))
    except (KeyError, IndexError):
        return template
