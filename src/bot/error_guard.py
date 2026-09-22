# src/bot/error_guard.py
"""全局异常守卫（内部实现）

- 定义致命与可恢复两级路由规则
- 实现异常到 GUI 信号的分发闭环
"""

import functools
import inspect
from collections.abc import Callable
from typing import Any, ParamSpec, TypeVar, cast

from exceptions import MAPS, BotError, ConfigError, ProxyError
from gui.mediator import gui_bridge
from utils.logger import get_logger

P = ParamSpec("P")
T = TypeVar("T")


def _describe(exc: BotError) -> str:
    """渲染异常详细文案"""
    if isinstance(exc, ConfigError):
        template = MAPS["Config"].get(type(exc), "")
    else:
        table = MAPS["Connectivity"]
        if isinstance(exc, ProxyError):
            template = table["Proxy"].get(type(exc), "")
        else:
            template = table.get(type(exc), "")
    try:
        return template.format(**vars(exc)) or type(exc).__name__
    except (KeyError, IndexError):
        return str(exc) or type(exc).__name__


def _route(exc: BotError, stage: str) -> None:
    """路由异常到 GUI 信号"""
    logger = get_logger("ErrorGuard")
    if gui_bridge.is_shutdown_pending():
        logger.debug(f"关闭流程中忽略异常（{stage}）")
        return

    detail = _describe(exc)
    if exc.fatal:
        logger.error(f"{stage}发生致命错误: {detail}")
        gui_bridge.request_fatal.emit(f"{stage}\n{detail}")
    else:
        logger.error(f"{stage}发生配置错误: {detail}")
        gui_bridge.request_force_setup.emit({})


def _route_unexpected(exc: Exception, stage: str) -> None:
    """未知异常致命路由"""
    logger = get_logger("ErrorGuard")
    if gui_bridge.is_shutdown_pending():
        logger.debug(f"关闭流程中忽略未知异常（{stage}）")
        return
    detail = f"{type(exc).__name__}: {exc}"
    logger.error(f"{stage}发生未预期错误: {detail}")
    gui_bridge.request_fatal.emit(f"{stage}\n{detail}")


def error_guard(
    stage: str, catch_all: bool = False, reraise: bool = False
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """异常兜底装饰器

    catch_all=True 连未知异常也接住，按致命路由
    reraise=True 路由信号后异常继续上抛（调用方自行中断）
    """
    guard_exceptions: tuple[type[Exception], ...] = (
        (BotError, Exception) if catch_all else (BotError,)
    )

    def _handle(exc: Exception) -> None:
        if isinstance(exc, BotError):
            _route(exc, stage)
        else:
            _route_unexpected(exc, stage)

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                try:
                    return await func(*args, **kwargs)
                except guard_exceptions as exc:
                    _handle(exc)
                    if reraise:
                        raise
                    return None

            return cast("Callable[P, T]", async_wrapper)

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except guard_exceptions as exc:
                _handle(exc)
                if reraise:
                    raise
                return None

        return wrapper

    return decorator
