"""控制器异常装饰器

- 异常兜底交给公共守卫，本件只交日志文案
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
    """报错落日志

    - 按钮事件不外弹
    """
    _logger.send_error(stage, exc)


def gui_guard(func: Callable[P, T]) -> Callable[P, T]:
    """GUI 按钮事件安全装饰器

    - 拦截业务异常并记日志
    - 日志按控制器与方法名点名
    """
    return guard(
        lambda self, *_args: MiscMessage.GUARD_EXEC_ERROR.format(
            name=f"{type(self).__name__}.{func.__name__}"
        ),
        _report,
        catch_all=True,
    )(func)
