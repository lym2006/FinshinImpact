# src/utils/init_files.py
"""文件初始化

- 实现必要文件检查与模板落盘
- 实例人设与内置默认模板按内容指纹对账
"""

import hashlib
from enum import Enum
from pathlib import Path

from .paths import (
    BOT_LOG,
    DEBUG_LOG,
    PERSONALITY_EXAMPLE,
    PERSONALITY_FILE,
    PERSONALITY_STAMP,
    RECORDS_DIR,
    TEMP_DIR,
)

_STAGED_DIR = RECORDS_DIR / "staged"


class PersonaSync(Enum):
    """人设模板对账结果

    - 启动日志与弹窗分派共用，禁裸写协议串
    """

    UNCHANGED = "unchanged"
    UPDATED = "updated"
    NOTIFY = "notify"


def _ensure_file_exists(target: Path, template: Path | None = None) -> None:
    """确保文件存在"""
    if target.exists():
        return

    target.parent.mkdir(parents=True, exist_ok=True)

    if template and template.exists():
        target.write_bytes(template.read_bytes())
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


def sync_persona_template() -> PersonaSync:
    """实例人设与内置默认模板对账

    - 戳记最近一次与该实例打交道的模板指纹
    - 副本内容等于戳所记的模板才判从未改动，直接换新
    - 从未改动判不出即只提示，绝不用模板覆盖实例副本
    - 提示后落当前模板指纹，同一版模板只提示一次
    """
    if not PERSONALITY_EXAMPLE.is_file():
        return PersonaSync.UNCHANGED
    template = _digest(PERSONALITY_EXAMPLE)
    stamp = _read_persona_stamp()

    if not PERSONALITY_FILE.is_file():
        _ensure_file_exists(PERSONALITY_FILE, PERSONALITY_EXAMPLE)
        _write_persona_stamp(template)
        return PersonaSync.UNCHANGED

    try:
        copy = _digest(PERSONALITY_FILE)
    except OSError:
        # 副本读不出时指纹无从比对，覆盖会毁掉读不到的内容
        return PersonaSync.UNCHANGED

    _write_persona_stamp(template)

    if copy == template:
        return PersonaSync.UNCHANGED
    if stamp == template:
        # 戳已等于当前模板，说明这一版已提示过
        return PersonaSync.UNCHANGED
    if copy == stamp:
        PERSONALITY_FILE.write_bytes(PERSONALITY_EXAMPLE.read_bytes())
        return PersonaSync.UPDATED
    return PersonaSync.NOTIFY


def init_project_files() -> None:
    """初始化项目必要文件"""
    for d in (TEMP_DIR, _STAGED_DIR):
        d.mkdir(parents=True, exist_ok=True)

    _ensure_file_exists(BOT_LOG)
    _ensure_file_exists(DEBUG_LOG)
