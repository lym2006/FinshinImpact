# src/bot/error_guard.py
"""Bot 线程异常守卫

- 致命与可恢复两级路由规则
- 将异常分发到对应的 GUI 信号
- 兜住调用那一半走本体公共件，这里只留分发
"""

from collections.abc import Callable
from typing import ParamSpec, TypeVar

from exceptions import (
    BotError,
    ConfigPathMissingError,
    describe_error,
)
from skin.messages import ConfigMessage, MiscMessage
from ui import gui_bridge
from utils.error_guard import guard
from utils.logger import get_logger

P = ParamSpec("P")
T = TypeVar("T")


def _setup_errors(exc: BotError) -> dict[str, str]:
    """向导字段级错误

    - 缺键异常须带字段标识，否则面板无标红
    - 整段缺失时 missing_key 是 section 名，字段键取点路径尾段
    """
    if isinstance(exc, ConfigPathMissingError):
        return {exc.key_path.rpartition(".")[2]: ConfigMessage.REQUIRED_MARK}
    return {}


def _route(exc: BotError, stage: str) -> None:
    """路由异常到 GUI 信号"""
    logger = get_logger("ErrorGuard")
    if gui_bridge.is_shutdown_pending():
        logger.debug(f"关闭流程中忽略异常（{stage}）")
        return

    logger.debug(exc)
    detail = describe_error(exc)
    if exc.fatal:
        logger.error(f"{stage}发生致命错误: {detail}")
        gui_bridge.request_notice.emit(f"{stage}\n{detail}", True)
    else:
        logger.error(f"{stage}发生配置错误: {detail}")
        gui_bridge.request_force_setup.emit(_setup_errors(exc))


def _route_unexpected(exc: Exception, stage: str) -> None:
    """未知异常致命路由

    - 面板只报到哪一步，异常本体与堆栈走调试日志
    """
    logger = get_logger("ErrorGuard")
    if gui_bridge.is_shutdown_pending():
        logger.debug(f"关闭流程中忽略未知异常（{stage}）")
        return
    logger.send_error(f"{stage}发生未预期错误", exc)
    gui_bridge.request_notice.emit(f"{stage}\n{MiscMessage.UNKNOWN_ERROR}", True)


def _handle(exc: Exception, stage: str) -> None:
    """收异常本体与哪一步，按两级分发"""
    if isinstance(exc, BotError):
        _route(exc, stage)
    else:
        _route_unexpected(exc, stage)


def error_guard(
    stage: str, catch_all: bool = False, reraise: bool = False
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """异常兜底装饰器

    - catch_all 为真时未知异常也按致命路由
    - reraise 为真时路由信号后继续上抛
    """
    return guard(stage, _handle, catch_all=catch_all, reraise=reraise)
