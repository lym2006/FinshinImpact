# src/utils/connectivity.py
"""连接性探测

- 代理与 Token 双重探测及构造期/请求期异常映射，校验轮与诊断轮共用
- attempt_channel 为预算内单次探测的唯一入口，超时折成字段错误不上抛
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
from messages import CheckMessage

from .config import PENDING_MARK
from .net_probe import FieldKey, probe_budget
from .ssl import SSLUnverifiedSession

# 构造期异常消息 → 配置键的解析规则
_SCHEME_RE = re.compile(r"Invalid scheme component:\s*(.*)", re.IGNORECASE)

__all__ = ["attempt_channel", "check_config", "map_construct_error"]


def map_construct_error(e: Exception, proxy: str) -> ConnectivityError:
    """映射构造期异常"""
    if isinstance(e, UnicodeError):
        # idna 域名标签非法（如 192..168.1.1）
        return ProxyAddressError(proxy=proxy)

    msg = str(e)
    m = _SCHEME_RE.search(msg)
    if m:
        scheme = m.group(1).strip() or CheckMessage.SCHEME_EMPTY
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

    - 构造期异常须映射为业务异常，防上层误判致命
    """
    try:
        SSLUnverifiedSession(proxy=proxy)
    except (ValueError, UnicodeError) as e:
        raise map_construct_error(e, proxy) from e


async def get_me(token: str, proxy: str) -> None:
    """探测 Token 有效性

    - 失败抛 ConnectivityError 族
    """
    bot: Bot | None = None
    try:
        session = SSLUnverifiedSession(proxy=proxy)
        bot = Bot(token=token, session=session)
        await bot.get_me()
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

    - proxy 先测，通过后再测 token
    - proxy 坏时 token 标记"暂未检测"而非"无效"
    """
    errors: dict[str, str] = {}
    proxy_text = ""

    try:
        await probe(proxy)
    except ConnectivityError as e:
        proxy_text = _err_text(e)

    if proxy_text:
        errors[FieldKey.PROXY] = proxy_text

        # 代理坏时请求出不了本机，getMe 结果无意义：标暂未检测而非无效
        errors[FieldKey.TOKEN] = CheckMessage.TOKEN_PENDING.format(mark=PENDING_MARK)
        return errors

    if not _is_token_wellformed(token):
        errors[FieldKey.TOKEN] = CheckMessage.TOKEN_BAD_FORMAT
        return errors

    try:
        await get_me(token, proxy)
    except TokenError as e:
        errors[FieldKey.TOKEN] = _err_text(e)
    except ConnectivityError as e:
        # getMe 阶段才暴露的网络问题归到 proxy
        errors[FieldKey.PROXY] = _err_text(e)

    return errors


async def attempt_channel(token: str, proxy: str) -> tuple[str | None, dict[str, str]]:
    """预算内单通道探测一次

    - 返回 (生效通道或 None, 错误字典)
    - 空错误即该通道通过
    - 预算按通道分层：直连是墙内黑洞快进快出，代理罩得住冷启动慢握手
    """
    try:
        errors = await asyncio.wait_for(
            check_config(token, proxy), timeout=probe_budget(proxy)
        )
    except TimeoutError:
        errors = {FieldKey.PROXY: CheckMessage.TIMEOUT}
    if not errors:
        return proxy, {}
    return None, errors


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
