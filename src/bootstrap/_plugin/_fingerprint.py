# src/bootstrap/_plugin/_fingerprint.py
"""已装库指纹

- 依赖并集摘要落 runtime，供升级后续装判定
"""

import hashlib

from core.domain import PluginFile

from ._support import RUNTIME_DIR, dev_mode

_FINGERPRINT = RUNTIME_DIR / PluginFile.FINGERPRINT


def installed_deps_digest(pins: list[str]) -> str:
    """计算依赖并集指纹

    - 行序无关，同集合必同摘要
    """
    return hashlib.sha256("\n".join(sorted(pins)).encode("utf-8")).hexdigest()


def save_fingerprint(digest: str) -> None:
    """写 runtime 已装指纹文件

    - 开发模式跳过，装库未成功不得调用
    """
    if dev_mode():
        return
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    _FINGERPRINT.write_text(digest, encoding="utf-8")


def read_fingerprint() -> str:
    """读 runtime 已装指纹，缺失返回空串"""
    if not _FINGERPRINT.is_file():
        return ""
    return _FINGERPRINT.read_text(encoding="utf-8").strip()
