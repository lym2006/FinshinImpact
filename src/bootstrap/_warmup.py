# src/bootstrap/_warmup.py
"""字节码预热

- 主窗就绪后后台补编源码字节码，下次启动导入直接命中缓存
- 限定项目源码目录，三方环境不重复编译
"""

import compileall
import threading

from profile_env import ROOT_DIR

# compileall 静默级别，只报错不打进度
_QUIET = 1

# 预热范围与线程名
_SRC_DIR = ROOT_DIR / "src"
_THREAD_NAME = "BytecodeWarmup"


def _compile_src() -> None:
    """增量编译源码为字节码，失败静默"""
    try:
        compileall.compile_dir(_SRC_DIR, quiet=_QUIET)
    except OSError:
        pass


def start_warmup() -> None:
    """后台线程启动字节码预热

    - 守护线程随进程退出，不阻塞也不影响本次启动
    """
    threading.Thread(target=_compile_src, daemon=True, name=_THREAD_NAME).start()
