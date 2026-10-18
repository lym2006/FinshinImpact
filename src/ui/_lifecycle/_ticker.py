# src/ui/_lifecycle/_ticker.py
"""定间隔计时泵

- QTimer 只在泵内持有，对外只走封装接口，回调逻辑留在各调用点
- 运行中重复 start 不重置计数，stop 随时可调
- 一次性延时由 after 代发，触发后不留句柄
"""

from collections.abc import Callable

from PySide6.QtCore import QObject, QTimer


class Ticker:
    """外置回调的计时壳

    - 间隔在构造期定死，启停生命周期归调用点
    - repeats 为 False 时作一次性超时，到点触发且仍可 stop
    """

    def __init__(
        self,
        parent: QObject,
        interval_ms: int,
        on_tick: Callable[[], None],
        *,
        repeats: bool = True,
    ) -> None:
        self._timer = QTimer(parent)
        self._timer.setSingleShot(not repeats)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(on_tick)

    def start(self) -> None:
        """启动计时，已在跑则保持原节拍"""
        if not self._timer.isActive():
            self._timer.start()

    def stop(self) -> None:
        """停止计时"""
        self._timer.stop()

    @staticmethod
    def after(delay_ms: int, on_tick: Callable[[], None]) -> None:
        """延时一次性触发

        - 即发即忘，不提供中途取消
        """
        QTimer.singleShot(delay_ms, on_tick)
