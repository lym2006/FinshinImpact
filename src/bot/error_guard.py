"""Bot 线程异常守卫

- 致命与可恢复两级路由规则
- 将异常分发到对应的 GUI 信号
"""

from collections.abc import Callable
from typing import ParamSpec, TypeVar

from exceptions import ConfigAttrError, ConfigPathMissingError, describe_error
from finshin_sdk.exceptions import BotError
from skin.messages import ConfigMessage, MiscMessage
from ui import gui_bridge
from utils import get_logger
from utils.config import FieldErrors
from utils.error_guard import guard

P = ParamSpec("P")
T = TypeVar("T")


def _setup_errors(exc: BotError) -> FieldErrors:
    """向导字段级错误

    - 带字段身份的异常须落到对应格子，否则面板无标红
    - 配置项身份直接当键，面板按同一身份找格子
    """
    if isinstance(exc, ConfigPathMissingError):
        return {exc.key_path: ConfigMessage.REQUIRED_MARK}
    if isinstance(exc, ConfigAttrError):
        return {exc.key_path: describe_error(exc)}
    return {}


def _route(exc: BotError, stage: str) -> None:
    """路由异常到 GUI 信号

    - 能落到字段的配置错误走向导，红字与 ⚠ 一起挂上
    - 其余 BotError 与普通未知异常同一出路
    """
    logger = get_logger("ErrorGuard")
    if gui_bridge.is_shutdown_pending():
        logger.debug(f"关闭流程中忽略异常（{stage}）")
        return

    detail = describe_error(exc)

    # 结论都印在窗上，日志只留调试级
    logger.debug(f"{stage}发生错误: {detail}")

    if exc.fatal:
        gui_bridge.request_notice.emit(f"{stage}\n{detail}", True)
        return

    errors = _setup_errors(exc)
    if errors:
        gui_bridge.request_force_setup.emit(errors)
        return

    _route_unexpected(exc, stage)


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
    """异常两级分发

    - 异常本体与出错环节一并收下
    """
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
