# src/ui/_windows/_controllers/_decorator.py
"""控制器异常装饰器

- 业务异常拦截，保障 GUI 线程存活
- 兜住调用那一半走本体公共件，这里只留日志那一句
"""

from collections.abc import Callable
from typing import ParamSpec, TypeVar

from skin.messages import MiscMessage
from utils import get_logger
from utils.error_guard import guard

_logger = get_logger("GUI.Guard")

# 泛型定义
P = ParamSpec("P")
T = TypeVar("T")


def _report(exc: Exception, stage: str) -> None:
    """拦截的报错只落日志，按钮事件不外弹"""
    _logger.send_error(stage, exc)


def gui_guard(func: Callable[P, T]) -> Callable[P, T]:
    """GUI 按钮事件安全装饰器

    - 拦截业务异常并记日志
    - 日志点名是哪只控制器，按钮派发都叫同名，只写方法名分不开
    """
    return guard(
        lambda self, *_args: MiscMessage.GUARD_EXEC_ERROR.format(
            name=f"{type(self).__name__}.{func.__name__}"
        ),
        _report,
        catch_all=True,
    )(func)
