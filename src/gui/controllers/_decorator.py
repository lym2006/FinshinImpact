# src/gui/controllers/_decorator.py
"""控制器异常装饰器

- 实现业务异常拦截，保障 GUI 线程存活
"""

from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar, cast

from messages import MiscMessage
from utils.logger import get_logger

_logger = get_logger("GUI.Guard")

# 泛型定义
P = ParamSpec("P")
T = TypeVar("T")


def gui_guard(func: Callable[P, T]) -> Callable[P, T]:
    """GUI 按钮事件安全装饰器

    - 拦截业务异常并记日志
    """

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T | None:
        try:
            return func(*args, **kwargs)

        except Exception as e:
            _logger.send_error(
                MiscMessage.GUARD_EXEC_ERROR.format(name=func.__name__), e
            )

        return

    return cast(Callable[P, T], wrapper)
