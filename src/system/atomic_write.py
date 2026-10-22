# src/system/atomic_write.py
"""同目录原子落盘

- 先写同目录临时件再改名，读侧只会看到旧版或新版整份内容
- 临时件名带随机后缀，同目录并发写各改各的
- 改名失败只清本次临时件，正式文件保持原样
"""

import os
import tempfile
from pathlib import Path


def write_text_atomic(target: Path, text: str) -> None:
    """原子写入文本

    - 临时件与目标同目录，改名不跨卷
    - 落盘先 fsync 再改名，断电不留半截
    - 写不进抛 OSError，由调用方决定提示或降级
    """
    directory = target.parent
    directory.mkdir(parents=True, exist_ok=True)

    fd, temp_name = tempfile.mkstemp(
        dir=directory, prefix=f".{target.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, target)
    except OSError:
        _discard(temp_name)
        raise


def write_bytes_atomic(target: Path, data: bytes) -> None:
    """原子写入字节

    - 供模板副本这类整份覆盖的二进制原文使用
    """
    directory = target.parent
    directory.mkdir(parents=True, exist_ok=True)

    fd, temp_name = tempfile.mkstemp(
        dir=directory, prefix=f".{target.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, target)
    except OSError:
        _discard(temp_name)
        raise


def _discard(temp_name: str) -> None:
    """清掉失败残留的临时件

    - 清不动也不改写主流程结论
    """
    try:
        os.unlink(temp_name)
    except OSError:
        pass
