# src/gui/controllers/_decorator.py
"""控制器异常装饰器（内部实现）

- 实现业务异常拦截，保障 GUI 线程存活
"""

from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar, cast

from utils.logger import get_logger

logger = get_logger("GUI.Guard")
P = ParamSpec("P")  # 泛型定义
T = TypeVar("T")


def gui_guard(func: Callable[P, T]) -> Callable[P, T]:
    """GUI 按钮事件安全装饰器

    拦截业务异常并记日志，防 GUI 线程卡死。
    """

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T | None:
        try:
            return func(*args, **kwargs)

        except Exception as e:
            logger.send_error(f"执行 [{func.__name__}] 时发生错误", e)

        return

    return cast(Callable[P, T], wrapper)
