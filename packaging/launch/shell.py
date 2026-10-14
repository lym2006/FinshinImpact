# packaging/launch/shell.py
"""启动器换壳交接

- 暂存的新壳换入规范路径，图标缓存刷新后拉起新进程
- 新旧进程靠引导锁轮询交接，旧壳退场后补删备份
"""

import shutil
import subprocess
import sys
import time
from pathlib import Path

from pack_spec import (
    CREATE_NO_WINDOW,
    DETACHED_PROCESS,
    SHELL_BAK_SUFFIX,
    SHELL_EXE,
    SHELL_PENDING,
)

from . import dialogs, instancelock

_ICON_REFRESH_TIMEOUT = 5.0  # 图标缓存刷新超时 5 秒
_SWAP_FAST_TIMEOUT = 5.0  # 快交接静默等待上限 5 秒
_SWAP_SOOTHE_MS = 20_000  # 慢路径安抚弹窗驻留 20 秒
_HANDOFF_POLL_TICK = 0.5  # 抢锁轮询间隔 0.5 秒

# 旧壳确认接管后才退场，交接瞬间 .old 仍被占用，收尾限时重试补删
_OLD_SHELL_WAIT = 10.0  # 补删旧壳备份总上限 10 秒
_OLD_SHELL_TICK = 0.5  # 补删重试间隔 0.5 秒


def apply_shell_update(root: Path, handoff: bool = False) -> None:
    """更换启动器本体

    - 启动开头调用只换文件，沿用当前流程
    - 升级收尾调用时拉起新版，新版取得引导锁后本进程退出，超时则本进程直接启动
    """
    pending = root / SHELL_PENDING
    exe_path = root / SHELL_EXE
    bak = exe_path.with_name(SHELL_EXE + SHELL_BAK_SUFFIX)

    # 先试删上次遗留的备份，旧壳未退场删不掉属预期，交本次启动收尾补删
    try:
        bak.unlink(missing_ok=True)
    except OSError:
        pass
    new_exe = pending / SHELL_EXE
    if not new_exe.is_file():
        return
    try:
        exe_path.rename(bak)  # 旧 exe 变身 .old 让位
    except OSError:
        # 改名失败可能是短暂占用，放弃本次更换，保留暂存下次再试
        print("启动器暂被占用，本次沿用旧版继续")
        return
    shutil.move(str(new_exe), str(exe_path))  # 新壳移入规范路径
    shutil.rmtree(pending, ignore_errors=True)

    # 换壳后 exe 路径与文件名未变，Shell 图标缓存认路径不认内容，不刷新则用户端沿用旧图标
    try:
        subprocess.run(
            ["ie4uinit.exe", "-show"],
            creationflags=CREATE_NO_WINDOW,
            timeout=_ICON_REFRESH_TIMEOUT,
        )
    except Exception:
        pass  # 系统裁剪或刷新超时都不值得拦换壳
    if not handoff:
        return

    subprocess.Popen([str(exe_path)], cwd=str(root), creationflags=DETACHED_PROCESS)

    # 快交接：新壳数秒内抢锁则用户全程无感
    if _handoff_wait(_SWAP_FAST_TIMEOUT):
        sys.exit(0)

    # 慢路径：新壳多半卡在杀软首扫，安抚窗顶住无反馈时间
    dialogs.wait_info(
        "更新完成，正在自动重新启动。\n首次启动需要安全软件扫描，可能要等一会儿…",
        _SWAP_SOOTHE_MS,
    )
    if _handoff_wait(_SWAP_FAST_TIMEOUT + _SWAP_SOOTHE_MS / 1000):
        sys.exit(0)
    print("新壳迟迟未接管（多半是被安全软件首扫拦下），本次由旧壳直接启动")


def retire_old_shell(root: Path) -> None:
    """补删换壳遗留的旧壳备份

    - 新壳启动收尾调用，旧壳退场释放文件后删掉
    - 超时删不掉留给下次启动换壳开头清，全程静默
    """
    bak = root / (SHELL_EXE + SHELL_BAK_SUFFIX)
    if not bak.is_file():
        return
    deadline = time.monotonic() + _OLD_SHELL_WAIT
    while time.monotonic() < deadline:
        try:
            bak.unlink(missing_ok=True)
            return
        except OSError:
            time.sleep(_OLD_SHELL_TICK)


def _handoff_wait(timeout: float) -> bool:
    """轮询等待新版取得引导锁

    - 新版弹出选择窗即持有引导锁，探测到锁被占用即判定接管完成
    - 选择窗停留期间锁保持占用，不会漏判
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if instancelock.bootstrap_taken():
            return True
        time.sleep(_HANDOFF_POLL_TICK)
    return False
