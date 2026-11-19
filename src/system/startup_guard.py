"""发布包入口的最后兜底"""

from collections.abc import Iterator
from contextlib import contextmanager

from .native_dialog import describe, show_error

_GUARD_TITLE = "Finshin Impact"

_GUARD_HEAD = "程序启动失败，包文件可能不完整"


@contextmanager
def startup_guard() -> Iterator[None]:
    """兜住入口异常

    - 弹系统消息后以失败码退出
    """
    try:
        yield
    except Exception as exc:
        # 样式层与界面库都可能正是坏掉的那个，这里只走标准库与系统消息框
        show_error(_GUARD_TITLE, f"{_GUARD_HEAD}\n{describe(exc)}")
        raise SystemExit(1) from exc
