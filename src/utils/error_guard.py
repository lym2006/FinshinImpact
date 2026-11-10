# src/utils/error_guard.py
"""异常兜底

- 定义包住一次调用的装饰器，同步与协程两种都接
- 捕获范围、是否重抛与反馈去向逐项由调用处点名
"""

import functools
import inspect
from collections.abc import Callable
from typing import Any, ParamSpec, TypeVar, cast

from exceptions import BotError

P = ParamSpec("P")
T = TypeVar("T")

# 反馈去向：收异常本体与「哪一步」，写日志还是上屏由它自己定
_Report = Callable[[Exception, str], None]

# 哪一步：写死一句，或按本次实参现算（装饰方法时要点名是哪个实例）
_Stage = str | Callable[..., str]


def _text_of(stage: _Stage, args: tuple[Any, ...]) -> str:
    """取这一次调用的步骤名"""
    return stage(*args) if callable(stage) else stage


def guard(
    stage: _Stage,
    report: _Report,
    *,
    catch_all: bool = False,
    reraise: bool = False,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """兜住一次调用的装饰器

    - catch_all 为真时表外异常也接住，为假时只接本族
    - reraise 为真时交代完继续上抛，为假时接住即完
    - 反馈去向只在被兜住那一刻调用一次
    - stage 可以是按本次实参现算的一句
    """
    caught: tuple[type[Exception], ...] = (
        (BotError, Exception) if catch_all else (BotError,)
    )

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                try:
                    return await func(*args, **kwargs)
                except caught as exc:
                    report(exc, _text_of(stage, args))
                    if reraise:
                        raise
                    return None

            return cast("Callable[P, T]", async_wrapper)

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except caught as exc:
                report(exc, _text_of(stage, args))
                if reraise:
                    raise
                return None

        return wrapper

    return decorator
