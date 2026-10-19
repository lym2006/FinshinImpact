# src/utils/lifecycle.py
"""生命周期（内部实现）

- 提供按对象注册的清理入口
- 实现自退注销与退出兜底
- 纯工具层：零日志，清理失败以描述列表返回上层记录
"""

import asyncio
import threading
from collections.abc import Callable
from typing import Any, Literal, cast

LifecycleType = Literal["hook_sync", "hook_async", "thread"]
TargetType = Callable | threading.Thread | None

_registry: dict[
    LifecycleType, list[tuple[TargetType, str, asyncio.AbstractEventLoop | None]]
] = {
    "hook_sync": [],
    "hook_async": [],
    "thread": [],
}

# 清理可能从多个线程并发进入，注册表读写必须串行
_registry_lock = threading.Lock()


def register_lifecycle(target: TargetType, desc: str, type_: LifecycleType) -> None:
    """注册生命周期资源"""
    with _registry_lock:
        # 绑定方法按 __self__ + __func__ 相等判定，同名不同实例不误伤
        if any(t == target for t, _, _ in _registry[type_]):
            return
        loop = asyncio.get_running_loop() if type_ == "hook_async" else None
        _registry[type_].append((target, desc, loop))


def unregister_lifecycle(target: TargetType, type_: LifecycleType) -> None:
    """资源自行退出时注销自己"""
    with _registry_lock:
        _registry[type_] = [x for x in _registry[type_] if x[0] != target]


def shutdown_all() -> list[str]:
    """进程退出兜底清理（线程安全且幂等）

    返回失败项描述列表，由调用方记录。
    """
    with _registry_lock:
        # _registry 恒含三个分类键，判空必须看各列表内容
        if not any(_registry.values()):
            return []
        failures = _run_shutdown()
        _registry.clear()
        return failures


def _run_shutdown() -> list[str]:
    """执行一轮完整清理，收集失败项"""
    failures: list[str] = []

    def _run_on_loop(
        coro: Any,
        desc: str,
        loop: asyncio.AbstractEventLoop,
        timeout: float = 5.0,
    ) -> None:
        """投递协程到 loop"""
        if not loop.is_running():
            # loop 已停：协程永远无人 await，手动 close 防退出警告
            failures.append(f"协程未执行（loop 未运行）: {desc}")
            coro.close()
            return
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        try:
            future.result(timeout=timeout)
        except TimeoutError:
            future.cancel()
            failures.append(f"协程超时 {timeout}s: {desc}")
        except Exception as e:
            failures.append(f"协程异常 [{desc}]: {type(e).__name__}: {e}")

    # 逆序清理：后注册先释放，三类互不阻断
    for hook, desc, _ in reversed(_registry["hook_sync"]):
        try:
            cast(Callable, hook)()
        except Exception as e:
            failures.append(f"同步钩子异常 [{desc}]: {type(e).__name__}: {e}")

    for hook, desc, loop in reversed(_registry["hook_async"]):
        if not loop:
            continue
        try:
            _run_on_loop(cast(Callable, hook)(), desc, loop)
        except Exception as e:
            failures.append(f"异步钩子异常 [{desc}]: {type(e).__name__}: {e}")

    # 线程 join 带超时：卡死的线程不拖死清理
    current = threading.current_thread()
    for thread, desc, _ in reversed(_registry["thread"]):
        thread = cast(threading.Thread, thread)
        if thread is current:
            # 清理链可能运行在被注册线程自己身上，join 自己必抛错
            continue
        if thread.is_alive():
            thread.join(timeout=3.0)
            if thread.is_alive():
                failures.append(f"线程停止失败: {desc}")

    return failures
