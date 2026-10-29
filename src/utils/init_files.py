# src/utils/init_files.py
"""文件初始化

- 实现必要文件检查与模板落盘
- 实例人设与内置默认模板按内容指纹对账
"""

import hashlib
from enum import StrEnum
from pathlib import Path

from system.atomic_write import write_bytes_atomic

from .paths import (
    DB_BACKUP_DIR,
    DB_DIR,
    PERSONA_DIR,
    PERSONA_FILE,
    PERSONA_STAMP,
    PERSONA_TEMPLATE,
    RECORDS_DIR,
)
from .persona import load_persona_cache, save_applied_persona


class PersonaSync(StrEnum):
    """人设模板对账结果

    - 启动日志与弹窗分派共用，禁裸写协议串
    """

    UNCHANGED = "unchanged"
    UPDATED = "updated"
    NOTIFY = "notify"


def _copy_if_missing(target: Path, template: Path) -> None:
    """目标缺失即从模板整份复制

    - 模板读不到即不建文件，交由调用方判定
    """
    if target.exists():
        return

    target.parent.mkdir(parents=True, exist_ok=True)

    if template.exists():
        write_bytes_atomic(target, template.read_bytes())


def _digest(path: Path) -> str:
    """取文件内容指纹

    - 按读文本再编码算，行尾转换不计入改动
    """
    return hashlib.sha256(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()


def _read_persona_stamp() -> str:
    """读人设对账戳

    - 缺失或读不出返回空串，按从未对过账处理
    """
    try:
        return PERSONA_STAMP.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _write_persona_stamp(digest: str) -> None:
    """落人设对账戳

    - 写不进不阻断启动，下次启动重走判定
    """
    try:
        PERSONA_STAMP.write_text(digest, encoding="utf-8")
    except OSError:
        pass


def _ensure_persona_copy() -> bool:
    """实例人设副本缺失即从内置默认模板建好

    - 副本已在即原样保留
    - 模板读不出或写不进返回 False
    """
    if PERSONA_FILE.is_file():
        return True
    try:
        template = _digest(PERSONA_TEMPLATE)
        _copy_if_missing(PERSONA_FILE, PERSONA_TEMPLATE)
    except OSError:
        return False
    _write_persona_stamp(template)
    return True


def apply_persona_template() -> bool:
    """用内置默认模板覆盖实例人设

    - 覆盖后落当前模板指纹、刷存档并按存档装填正文
    - 读写失败返回 False
    """
    try:
        template = _digest(PERSONA_TEMPLATE)
        text = PERSONA_TEMPLATE.read_text(encoding="utf-8")
        write_bytes_atomic(PERSONA_FILE, PERSONA_TEMPLATE.read_bytes())
    except OSError:
        return False
    if not save_applied_persona(text):
        return False
    _write_persona_stamp(template)
    load_persona_cache()
    return True


def save_persona_text(text: str) -> bool:
    """把正文写进实例人设副本

    - 副本缺失即先从模板建好
    - 对账戳不动，写过的副本按用户改动版处理
    - 写不进返回 False，副本保持原样
    """
    if not _ensure_persona_copy():
        return False
    try:
        write_bytes_atomic(PERSONA_FILE, text.encode("utf-8"))
    except OSError:
        return False
    return True


def mark_persona_prompted() -> None:
    """落本次提示的已送达记录

    - 提示窗关掉才记这一版模板已打过交道，同一版只提示一次
    """
    if PERSONA_TEMPLATE.is_file():
        _write_persona_stamp(_digest(PERSONA_TEMPLATE))


def sync_persona_template() -> PersonaSync:
    """实例人设与内置默认模板对账

    - 戳记最近一次与该实例打交道的模板指纹
    - 副本内容等于戳所记的模板才判从未改动，直接换新
    - 从未改动判不出即只提示，绝不用模板覆盖实例副本
    - 提示未送达即不落戳，下次启动接着提示
    - 换新写不进退回提示路径，由用户当场处置
    """
    if not PERSONA_TEMPLATE.is_file():
        return PersonaSync.UNCHANGED
    template = _digest(PERSONA_TEMPLATE)
    stamp = _read_persona_stamp()

    if not _ensure_persona_copy():
        return PersonaSync.UNCHANGED

    try:
        copy = _digest(PERSONA_FILE)
    except OSError:
        # 副本读不出时指纹无从比对，覆盖会毁掉读不到的内容
        return PersonaSync.UNCHANGED

    if copy == template:
        _write_persona_stamp(template)
        return PersonaSync.UNCHANGED
    if stamp == template:
        # 戳等于当前模板即本版已提示过，同一版不重复打扰
        return PersonaSync.UNCHANGED
    if copy == stamp:
        return PersonaSync.UPDATED if apply_persona_template() else PersonaSync.NOTIFY
    return PersonaSync.NOTIFY


def init_project_files() -> None:
    """初始化实例运行所需目录"""
    # sqlite3 只建库文件不建父目录，父目录缺失即打不开库
    for d in (RECORDS_DIR, DB_DIR, DB_BACKUP_DIR, PERSONA_DIR):
        d.mkdir(parents=True, exist_ok=True)
