# src/gui/signal.py
"""安全信号（内部实现）

- 定义按 tag 防重连的信号包装
"""

from typing import Any, overload

from PySide6.QtCore import QObject, Qt, Signal, SignalInstance


class SafeSignalInstance:
    """防重连信号实例包装"""

    def __init__(self, instance: SignalInstance) -> None:
        self._instance = instance
        self._connected: set[str] = set()  # 记录已连接 tag
        self._slots: dict[str, object] = {}  # tag 对应的原始槽，供 disconnect

    def connect(
        self,
        slot: object,
        tag: str,
        queued: bool = False,
    ) -> None:
        """同一 tag 只连接一次"""
        if tag in self._connected:
            return
        self._connected.add(tag)
        self._slots[tag] = slot
        if queued:
            self._instance.connect(slot, Qt.ConnectionType.QueuedConnection)
        else:
            self._instance.connect(slot)

    def disconnect(self, tag: str) -> None:
        """按 tag 摘除连接"""
        slot = self._slots.pop(tag, None)
        if slot is not None:
            self._instance.disconnect(slot)
            self._connected.discard(tag)

    def emit(self, *args: Any) -> None:
        """发射信号（仅触达本信号的槽）"""
        self._instance.emit(*args)


class SafeSignal:
    """防重连信号描述符

    将宿主类上的 _signal_<name> 真实信号包装为入口。
    """

    _native_attr: str

    def __set_name__(self, owner: type, name: str) -> None:
        self._native_attr = f"_signal_{name}"

    @overload
    def __get__(self, instance: None, owner: Any = None) -> "SafeSignal": ...

    @overload
    def __get__(self, instance: QObject, owner: Any = None) -> SafeSignalInstance: ...

    def __get__(self, instance: QObject | None, owner: Any = None) -> Any:
        if instance is None:
            return self
        # 包装实例按描述符缓存，保证 tag 去重集合稳定存活
        cache: dict = instance.__dict__.setdefault("_safe_signal_cache", {})
        if self not in cache:
            cache[self] = SafeSignalInstance(getattr(instance, self._native_attr))
        return cache[self]


__all__ = ["SafeSignal", "SafeSignalInstance", "Signal"]
