# src/utils/init_files.py
"""路径与文件初始化

- 按实例身份码派生实例根目录与其下配置、人设、数据路径
- 实现必要文件检查与模板落盘
"""

from pathlib import Path

from core.domain import Platform, platform_of_profile
from exceptions import ProfileMissingError
from profile_env import (
    ASSET_PERSONA_EXAMPLE_NAME,
    ASSETS_DIR,
    INSTANCE_PERSONA_NAME,
    get_profile,
    profile_dir,
)

# 平台模板
_TG_EXAMPLE = "config.telegram.example.toml"
_QQ_EXAMPLE = "config.qq.example.toml"

# 身份码前缀即平台来源，未知前缀回落 Telegram
_PLATFORM_EXAMPLES = {Platform.TELEGRAM: _TG_EXAMPLE, Platform.QQ: _QQ_EXAMPLE}

# 身份码在 bootstrap 写完环境变量后才首次导入本模块，此处取值即冻结
_PROFILE = get_profile()
if not _PROFILE:
    # 空身份码拼进路径就是 instances 根本身，实例资产会互相覆盖，只能直接死
    raise ProfileMissingError() from None

_PROFILE_DIR = profile_dir(_PROFILE)

CONFIG_FILE = _PROFILE_DIR / "config.toml"
PERSONALITY_FILE = _PROFILE_DIR / INSTANCE_PERSONA_NAME

# 运行时记录按实例拆分，防止污染
RECORDS_DIR = _PROFILE_DIR / "data/ai_records"
TEMP_DIR = RECORDS_DIR / "temp"
_STAGED_DIR = RECORDS_DIR / "staged"

# 帮助图属实例产物，落实例数据目录，不与 data 按实例隔离冲突
HELP_IMAGE = _PROFILE_DIR / "data/help.png"

# 日志按实例拆分，共用目录会互相污染且 GUI 打不开对应实例的记录
LOGS_DIR = _PROFILE_DIR / "logs"
BOT_LOG = LOGS_DIR / "bot.log"
DEBUG_LOG = LOGS_DIR / "debug.log"

# 身份码前缀不属已知平台时回落 Telegram
_PLATFORM = platform_of_profile(_PROFILE) or Platform.TELEGRAM
CONFIG_EXAMPLE = ASSETS_DIR / _PLATFORM_EXAMPLES.get(_PLATFORM, _TG_EXAMPLE)
_PERSONALITY_EXAMPLE = ASSETS_DIR / ASSET_PERSONA_EXAMPLE_NAME


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

    _ensure_file_exists(PERSONALITY_FILE, _PERSONALITY_EXAMPLE)
