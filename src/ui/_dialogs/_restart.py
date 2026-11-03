# src/ui/_dialogs/_restart.py
"""热重启等待窗

- 只由信号驱动的开与收，重启进行中窗上不给用户出口
- 重启成功把窗原地换成结果，等用户点确定才走
- 进程级唯一实例，重复开窗原地返回同一只
"""

from typing import TYPE_CHECKING

from skin.messages import EngineMessage

from ._wait import WaitDialog

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget

_window: WaitDialog | None = None  # 进程级唯一实例，窗关了即交还对象


def show_restart_wait(owner: "QWidget | None") -> None:
    """起一只热重启等待窗

    - 窗已在则原地返回，双信号不会叠窗
    """
    global _window
    if _window is not None:
        return
    _window = WaitDialog(EngineMessage.RESTARTING, parent=owner)
    _window.finished.connect(_give_back)
    _window.show()


def finish_restart_wait(text: str) -> bool:
    """把等待窗原地换成结果

    - 没窗即返回 False，结果话术由调用方另找地方说
    """
    if _window is None:
        return False
    _window.finish(text)
    return True


def close_restart_wait() -> None:
    """收掉热重启等待窗

    - 重启半路报错才走这里，成功那条交给结果窗等用户确认
    """
    if _window is not None:
        _window.accept()


def _give_back(_result: int) -> None:
    """窗关了交还对象，免得留着已销毁的窗"""
    global _window
    _window = None
