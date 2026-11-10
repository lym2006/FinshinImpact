# src/system/startup_guard.py
"""发布包入口的最后兜底

- 主程序导入之前就炸时，双击本没有任何出口，这里补一句系统弹窗
"""

from collections.abc import Iterator
from contextlib import contextmanager

from .native_dialog import describe, show_error

_GUARD_TITLE = "Finshin Impact"

_GUARD_HEAD = "程序启动失败，包文件可能不完整"


@contextmanager
def startup_guard() -> Iterator[None]:
    """接住入口脚本里的异常，弹一句再按失败退出"""
    try:
        yield
    except Exception as exc:
        # 样式层与界面库都可能正是坏掉的那个，这里只走标准库与系统消息框
        show_error(_GUARD_TITLE, f"{_GUARD_HEAD}\n{describe(exc)}")
        raise SystemExit(1) from exc
