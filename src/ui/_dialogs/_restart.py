# src/ui/_dialogs/_restart.py
"""热重启等待窗

- 只由信号驱动的开与关，窗上不给用户出口
- 进程级唯一实例，重复开窗原地返回同一只
- 关窗即交还对象，免得 Qt 侧留着已销毁的窗
"""

from typing import TYPE_CHECKING

from skin.messages import EngineMessage

from ._wait import WaitDialog

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget

_window: WaitDialog | None = None  # 进程级唯一实例，重复起 restart 只换文案


def show_restart_wait(owner: "QWidget | None") -> None:
    """起一只热重启等待窗

    - 窗已在则原地返回，双信号不会叠窗
    """
    global _window
    if _window is not None:
        return
    _window = WaitDialog(EngineMessage.RESTARTING, parent=owner)
    _window.show()


def close_restart_wait() -> None:
    """收掉热重启等待窗

    - 无窗即直接返回，跳过重启那条路一趟信号也不会发
    """
    global _window
    if _window is None:
        return
    _window.accept()
    _window = None
