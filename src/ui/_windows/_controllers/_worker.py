# src/ui/_windows/_controllers/_worker.py
"""控制器跑线程的公共收尾"""

from typing import Any

from PySide6.QtCore import QThread, SignalInstance

from ..._dialogs import WaitDialog


def run_waiting_worker(
    dialog: WaitDialog, worker: QThread, done: SignalInstance
) -> list[tuple[Any, ...]]:
    """起线程跑一轮回执，等窗关闭后收尾并交出攒下的帧

    - 帧的第一项是文案、末项是成败，中间项由各自的线程自定
    - 用户先行关窗时交回空表
    """
    frames: list[tuple[Any, ...]] = []

    def _collect(*args: Any) -> None:

        # 先存结果再收窗：finish 自动 accept，防暂存被 disconnect 掐断
        frames.append(args)
        dialog.finish(args[0], args[-1])

    done.connect(_collect)
    worker.start()
    try:
        dialog.exec()
    finally:
        # 用户先行关窗：摘除回执防迟到结果触碰已关窗口
        done.disconnect()
        worker.requestInterruption()
        worker.wait()
    return frames
