# src/utils/check/_connectivity.py
"""连接性探测

- 代理与 Token 两级探测，校验轮与诊断轮共用
- 构造期与请求期异常映射为字段错误，超时不上抛
"""

import asyncio
import re
from collections.abc import Awaitable, Callable

import aiohttp_socks
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
from skin.messages import CheckMessage, ConfigMessage

from ..network.probe import probe_budget
from ._fields import TelegramFieldKey

# 构造期异常消息 → 配置键的解析规则
_SCHEME_RE = re.compile(r"Invalid scheme component:\s*(.*)", re.IGNORECASE)


def _map_construct_error(e: Exception, proxy: str) -> ConnectivityError:
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
    from aiogram.exceptions import TelegramNetworkError, TelegramUnauthorizedError

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


async def _probe_proxy(proxy: str) -> None:
    """纯代理探测

    - 构造期异常须映射为业务异常，防上层误判致命
    """
    from ..network import SSLUnverifiedSession

    try:
        SSLUnverifiedSession(proxy=proxy)
    except (ValueError, UnicodeError) as e:
        raise _map_construct_error(e, proxy) from e


async def get_me(token: str, proxy: str) -> None:
    """探测 Token 有效性

    - 失败抛 ConnectivityError 族
    """
    from aiogram import Bot

    from ..network import SSLUnverifiedSession

    bot: Bot | None = None
    try:
        # 探测轮的成败属配置校验不属引擎链路，喂进断连状态机会误弹计时框
        session = SSLUnverifiedSession(proxy=proxy, report_link=False)
        bot = Bot(token=token, session=session)
        await bot.get_me()
    except TimeoutError as e:
        # 无代理时超时是直连不通，不能报"连接代理超时"的空地址文案
        raise (ProxyTimeoutError(proxy=proxy) if proxy else DirectTimeoutError()) from e
    except (ValueError, UnicodeError) as e:
        # 构造期异常穿透兜底（正常流程已在 _probe_proxy 拦截）
        raise _map_construct_error(e, proxy) from e
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


def preload_engine() -> None:
    """预触引擎导入链

    - 须在轮次首帧点亮通道行之前调用
    """
    # aiogram 经 PEP 562 懒加载，首触约 5 秒同步导入会饿死 wait_for 与界面倒计时
    from aiogram import Bot as _Bot  # noqa: F401

    from ..network import SSLUnverifiedSession as _Session  # noqa: F401


async def _check_config(
    token: str,
    proxy: str,
    probe: Callable[[str], Awaitable[None]] = _probe_proxy,
    get_me: Callable[[str, str], Awaitable[None]] = get_me,
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
        errors[TelegramFieldKey.PROXY] = proxy_text

        # 代理坏时请求出不了本机，getMe 结果无意义：标暂未检测而非无效
        errors[TelegramFieldKey.TOKEN] = CheckMessage.TOKEN_PENDING.format(
            mark=ConfigMessage.PENDING_MARK
        )
        return errors

    if not _is_token_wellformed(token):
        errors[TelegramFieldKey.TOKEN] = CheckMessage.TOKEN_BAD_FORMAT
        return errors

    try:
        await get_me(token, proxy)
    except TokenError as e:
        errors[TelegramFieldKey.TOKEN] = _err_text(e)
    except ConnectivityError as e:
        # getMe 阶段才暴露的网络问题归到 proxy
        errors[TelegramFieldKey.PROXY] = _err_text(e)

    return errors


async def attempt_channel(token: str, proxy: str) -> tuple[str | None, dict[str, str]]:
    """预算内探测单个通道

    - 轮次入口已在首帧前预触引擎，此处兜底端口复测等直调方
    - 返回 (生效通道或 None, 错误字典)
    - 空错误即该通道通过
    - 超时预算按通道类型取值，直连短、代理长
    """
    preload_engine()
    try:
        errors = await asyncio.wait_for(
            _check_config(token, proxy), timeout=probe_budget(proxy)
        )
    except TimeoutError:
        errors = {TelegramFieldKey.PROXY: CheckMessage.TIMEOUT}
    if not errors:
        return proxy, {}
    return None, errors


def _err_text(e: ConnectivityError) -> str:
    """生成可读错误文案"""
    from exceptions import MAP_KEY_CONNECTIVITY, MAP_KEY_PROXY, MAPS

    proxy_map = MAPS[MAP_KEY_CONNECTIVITY][MAP_KEY_PROXY]
    template = proxy_map.get(type(e)) or MAPS[MAP_KEY_CONNECTIVITY].get(type(e))
    if not template:
        return type(e).__name__
    try:
        return template.format(**vars(e))
    except (KeyError, IndexError):
        return template
