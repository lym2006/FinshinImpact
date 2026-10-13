# src/utils/init_files.py
"""文件初始化

- 实现必要文件检查与模板落盘
"""

from pathlib import Path

from .paths import (
    BOT_LOG,
    DEBUG_LOG,
    PERSONALITY_EXAMPLE,
    PERSONALITY_FILE,
    RECORDS_DIR,
    TEMP_DIR,
)

_STAGED_DIR = RECORDS_DIR / "staged"


def _ensure_file_exists(target: Path, template: Path | None = None) -> None:
    """确保文件存在"""
    if target.exists():
        return

    target.parent.mkdir(parents=True, exist_ok=True)

    if template and template.exists():
        target.write_bytes(template.read_bytes())
        return


def init_project_files() -> None:
    """初始化项目必要文件"""
    for d in (TEMP_DIR, _STAGED_DIR):
        d.mkdir(parents=True, exist_ok=True)

    _ensure_file_exists(BOT_LOG)
    _ensure_file_exists(DEBUG_LOG)

    _ensure_file_exists(PERSONALITY_FILE, PERSONALITY_EXAMPLE)
