# src/utils/init_files.py
"""文件初始化

- 实现必要文件检查与模板落盘
- 实例人设与内置默认模板按内容指纹对账
"""

import hashlib
from enum import Enum, StrEnum
from pathlib import Path

from system.atomic_write import write_bytes_atomic

from .paths import (
    BOT_LOG,
    DEBUG_LOG,
    PERSONALITY_EXAMPLE,
    PERSONALITY_FILE,
    PERSONALITY_STAMP,
    TEMP_DIR,
)
from .persona import reset_persona_cache


class PersonaSync(Enum):
    """人设模板对账结果

    - 启动日志与弹窗分派共用，禁裸写协议串
    """

    UNCHANGED = "unchanged"
    UPDATED = "updated"
    NOTIFY = "notify"


class PersonaState(StrEnum):
    """实例副本与内置默认模板的关系

    - 预览弹窗的状态提示与对账判定共用，禁裸写协议串
    """

    SAME = "same"
    OUTDATED = "outdated"
    EDITED = "edited"
    UNREADABLE = "unreadable"


def _ensure_file_exists(target: Path, template: Path | None = None) -> None:
    """确保文件存在"""
    if target.exists():
        return

    target.parent.mkdir(parents=True, exist_ok=True)

    if template and template.exists():
        write_bytes_atomic(target, template.read_bytes())
        return


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
        return PERSONALITY_STAMP.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _write_persona_stamp(digest: str) -> None:
    """落人设对账戳

    - 写不进不阻断启动，下次启动重走判定
    """
    try:
        PERSONALITY_STAMP.write_text(digest, encoding="utf-8")
    except OSError:
        pass


def ensure_persona_copy() -> bool:
    """实例人设副本缺失即从内置默认模板建好

    - 副本已在即原样保留
    - 模板读不出或写不进返回 False
    """
    if PERSONALITY_FILE.is_file():
        return True
    try:
        template = _digest(PERSONALITY_EXAMPLE)
        _ensure_file_exists(PERSONALITY_FILE, PERSONALITY_EXAMPLE)
    except OSError:
        return False
    _write_persona_stamp(template)
    return True


def apply_persona_template() -> bool:
    """用内置默认模板覆盖实例人设

    - 覆盖后落当前模板指纹并重置进程内人设缓存
    - 读写失败返回 False，实例副本保持原样
    """
    try:
        template = _digest(PERSONALITY_EXAMPLE)
        write_bytes_atomic(PERSONALITY_FILE, PERSONALITY_EXAMPLE.read_bytes())
    except OSError:
        return False
    _write_persona_stamp(template)
    reset_persona_cache()
    return True


def mark_persona_prompted() -> None:
    """落本次提示的已送达记录

    - 提示窗关掉才记这一版模板已打过交道，同一版只提示一次
    """
    if PERSONALITY_EXAMPLE.is_file():
        _write_persona_stamp(_digest(PERSONALITY_EXAMPLE))


def check_persona_state() -> PersonaState:
    """比对副本、模板与对账戳

    - 只读三方指纹不动磁盘，任一读不出归为不可判定
    """
    try:
        copy = _digest(PERSONALITY_FILE)
        template = _digest(PERSONALITY_EXAMPLE)
    except OSError:
        return PersonaState.UNREADABLE
    if copy == template:
        return PersonaState.SAME
    if copy == _read_persona_stamp():
        return PersonaState.OUTDATED
    return PersonaState.EDITED


def sync_persona_template() -> PersonaSync:
    """实例人设与内置默认模板对账

    - 戳记最近一次与该实例打交道的模板指纹
    - 副本内容等于戳所记的模板才判从未改动，直接换新
    - 从未改动判不出即只提示，绝不用模板覆盖实例副本
    - 提示未送达即不落戳，下次启动接着提示
    - 换新写不进退回提示路径，由用户当场处置
    """
    if not PERSONALITY_EXAMPLE.is_file():
        return PersonaSync.UNCHANGED
    template = _digest(PERSONALITY_EXAMPLE)
    stamp = _read_persona_stamp()

    if not ensure_persona_copy():
        return PersonaSync.UNCHANGED

    try:
        copy = _digest(PERSONALITY_FILE)
    except OSError:
        # 副本读不出时指纹无从比对，覆盖会毁掉读不到的内容
        return PersonaSync.UNCHANGED

    if copy == template:
        _write_persona_stamp(template)
        return PersonaSync.UNCHANGED
    if stamp == template:
        # 戳等于当前模板即本版已提示过，不再重复打扰
        return PersonaSync.UNCHANGED
    if copy == stamp:
        return PersonaSync.UPDATED if apply_persona_template() else PersonaSync.NOTIFY
    return PersonaSync.NOTIFY


def init_project_files() -> None:
    """初始化项目必要文件"""
    for d in (TEMP_DIR,):
        d.mkdir(parents=True, exist_ok=True)

    _ensure_file_exists(BOT_LOG)
    _ensure_file_exists(DEBUG_LOG)
