# src/utils/_single_instance.py
"""单实例守卫（内部实现）

- 命名互斥体锁定整机唯一实例，防双开互踩配置与 Telegram 长轮询
"""

import ctypes
from ctypes import wintypes

_ERROR_ALREADY_EXISTS = 183
_CloseHandle = ctypes.windll.kernel32.CloseHandle
_CreateMutexW = ctypes.windll.kernel32.CreateMutexW
_CreateMutexW.restype = wintypes.HANDLE  # 缺省 int 会在 64 位截断句柄

# 与启动器 _MUTEX_NAME 是同一把锁，两处改名必须同步
_MUTEX_NAME = "Local\\TelegramBot-Instance"

_instance_handle: int | None = None  # 持有至进程退出，由操作系统负责释放


def acquire_instance_lock() -> bool:
    """占用实例锁

    锁名固定：一台机器同时只许一个实例，同 token 双开必互踩。
    句柄与进程同生命周期，故意不关。
    """
    global _instance_handle
    handle = _CreateMutexW(None, False, _MUTEX_NAME)
    if not handle:
        return True  # 创建失败属异常环境，放行优于误拒
    if ctypes.GetLastError() == _ERROR_ALREADY_EXISTS:
        _CloseHandle(handle)
        return False
    _instance_handle = handle
    return True
