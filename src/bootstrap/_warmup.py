"""字节码预热

- 后台补编源码与三方库字节码
"""

import compileall
import sysconfig
import threading
from pathlib import Path

from system.profile_env import ROOT_DIR

# compileall 静默级别，只报错不打进度
_QUIET = 1

_THREAD_NAME = "BytecodeWarmup"

# 预热范围：项目源码与当前解释器的三方库目录
_THIRD_PARTY_DIR = Path(sysconfig.get_path("purelib"))


def _compile_dirs() -> list[Path]:
    """收集存在的预热目录"""
    return [path for path in (ROOT_DIR / "src", _THIRD_PARTY_DIR) if path.is_dir()]


def _compile_src() -> None:
    """预热目录的增量编译

    - 编译失败静默
    """
    for path in _compile_dirs():
        try:
            compileall.compile_dir(path, quiet=_QUIET)
        except OSError:
            pass


def start_warmup() -> None:
    """后台线程启动字节码预热"""
    threading.Thread(target=_compile_src, daemon=True, name=_THREAD_NAME).start()
