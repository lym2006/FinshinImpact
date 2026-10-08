# src/instance_lock.py
"""单实例守卫

- 命名互斥体锁定同账号唯一实例，防双开互踩配置与 Telegram 长轮询
"""

import ctypes
from ctypes import wintypes

from profile_env import get_profile

_ERROR_ALREADY_EXISTS = 183
_CloseHandle = ctypes.windll.kernel32.CloseHandle
_CreateMutexW = ctypes.windll.kernel32.CreateMutexW
_CreateMutexW.restype = wintypes.HANDLE  # 缺省 int 会在 64 位截断句柄

_MUTEX_PREFIX = "Local\\FinshinImpact-"

# 选 bot 窗口期间专用，与实例锁分离才能放行第二个 bot 的选择窗
_BOOTSTRAP_MUTEX_NAME = _MUTEX_PREFIX + "Bootstrap"

_instance_handle: int | None = None  # 持有至进程退出，由操作系统负责释放
_bootstrap_handle: int | None = None  # 同上，由 release_bootstrap_lock 主动释放


def _instance_mutex_name() -> str:
    """实例锁名

    - 统一入口保证锁名前身份码已就位
    - 身份码万一为空，空后缀锁全机共用，误拦优于放行双开
    """
    return _MUTEX_PREFIX + get_profile()


def _create(name: str) -> tuple[int | None, bool]:
    """创建命名互斥体

    - 返回 (持有的句柄, 是否抢到)
    - 创建失败属异常环境，放行优于误拒
    """
    handle = _CreateMutexW(None, False, name)
    if not handle:
        return None, True
    if ctypes.GetLastError() == _ERROR_ALREADY_EXISTS:
        _CloseHandle(handle)
        return None, False
    return handle, True


def acquire_instance_lock() -> bool:
    """占用实例锁

    - 锁名带身份码：同账号双开必互踩，不同账号各自放行
    - 唯一调用方是引导层，主程序不重复抢
    """
    global _instance_handle
    handle, acquired = _create(_instance_mutex_name())
    if not acquired:
        return False

    _instance_handle = handle
    return True


def acquire_bootstrap_lock() -> bool:
    """占用引导锁"""
    global _bootstrap_handle
    handle, acquired = _create(_BOOTSTRAP_MUTEX_NAME)
    if not acquired:
        return False

    _bootstrap_handle = handle
    return True


def release_bootstrap_lock() -> None:
    """释放引导锁

    - 身份码定案即释放，让运行期间双击启动器仍能开新的选择窗
    """
    global _bootstrap_handle
    if _bootstrap_handle is None:
        return

    _CloseHandle(_bootstrap_handle)
    _bootstrap_handle = None
