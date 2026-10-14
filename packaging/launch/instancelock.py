# packaging/launch/instancelock.py
"""引导锁静默探测

- 命名互斥体只探测不持有，占用判定交启动器决策
"""

import ctypes
from ctypes import wintypes

# 与主程序 instance_lock 的引导锁是同一把，两处改名必须同步
# 实例锁名带身份码、启动器无从得知，故只探测引导锁防重复弹选择窗
_BOOTSTRAP_MUTEX_NAME = "Local\\FinshinImpact-Bootstrap"
_ERROR_ALREADY_EXISTS = 183

_CreateMutexW = ctypes.windll.kernel32.CreateMutexW
_CreateMutexW.restype = wintypes.HANDLE  # 缺省 int 会在 64 位截断句柄
_CloseHandle = ctypes.windll.kernel32.CloseHandle


def bootstrap_taken() -> bool:
    """静默探测引导锁是否被占用"""
    handle = _CreateMutexW(None, False, _BOOTSTRAP_MUTEX_NAME)
    if not handle:
        return False
    busy = ctypes.GetLastError() == _ERROR_ALREADY_EXISTS
    _CloseHandle(handle)
    return busy
