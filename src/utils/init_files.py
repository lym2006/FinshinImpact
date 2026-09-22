# src/utils/init_files.py
"""路径与文件初始化（内部实现）

- 定义 data/logs 与配置文件唯一路径
- 实现必要文件检查与模板落盘
"""

from pathlib import Path

from exceptions import ConfigTemplateMissingError

from ._root_dir import ROOT_DIR

# ==================== 路径单一来源 ====================

RECORDS_DIR = ROOT_DIR / "data/ai_records"
TEMP_DIR = RECORDS_DIR / "temp"
STAGED_DIR = RECORDS_DIR / "staged"
DOCS_DIR = ROOT_DIR / "data/docs"
BLACKLIST_DIR = ROOT_DIR / "data/blacklists"
BLACKLIST_FILE = BLACKLIST_DIR / "blacklist.txt"
CONFIG_FILE = ROOT_DIR / "config.toml"
CONFIG_EXAMPLE = ROOT_DIR / "config.example.toml"
LOGS_DIR = ROOT_DIR / "logs"
BOT_LOG = LOGS_DIR / "bot.log"
DEBUG_LOG = LOGS_DIR / "debug.log"

# ==================== 文件创建 ====================


def ensure_file_exists(target: Path, template: Path | None = None) -> None:
    """确保文件存在"""
    if target.exists():
        return

    target.parent.mkdir(parents=True, exist_ok=True)

    if template and template.exists():
        target.write_bytes(template.read_bytes())
        return

    if template is not None:
        # 只有检查配置文件时会传入模板路径，其他时候不会抛出这个异常
        raise ConfigTemplateMissingError() from None


# ==================== 项目文件初始化 ====================


def init_project_files() -> None:
    """初始化项目必要文件"""
    for d in (TEMP_DIR, DOCS_DIR, STAGED_DIR):
        d.mkdir(parents=True, exist_ok=True)

    ensure_file_exists(BLACKLIST_FILE)
    ensure_file_exists(BOT_LOG)
    ensure_file_exists(DEBUG_LOG)
