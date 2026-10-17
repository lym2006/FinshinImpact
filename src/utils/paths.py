# src/utils/paths.py
"""实例路径单源

- 按实例身份码派生实例根目录与其下配置、人设、数据、日志路径
- 导入期身份码必须已由 bootstrap 写入，取值即冻结
"""

from core.domain import Platform, platform_of_profile
from exceptions import ProfileMissingError
from system.profile_env import (
    ASSET_PERSONA_EXAMPLE_NAME,
    ASSETS_DIR,
    INSTANCE_PERSONA_NAME,
    get_profile,
    profile_dir,
)

_PROFILE = get_profile()
if not _PROFILE:
    # 空身份码拼进路径就是 instances 根本身，实例资产会互相覆盖，只能直接死
    raise ProfileMissingError() from None

PROFILE_DIR = profile_dir(_PROFILE)

# 身份码前缀即平台来源，不属已知平台时回落 Telegram
PLATFORM = platform_of_profile(_PROFILE) or Platform.TELEGRAM

CONFIG_FILE = PROFILE_DIR / "config.toml"
PERSONALITY_FILE = PROFILE_DIR / INSTANCE_PERSONA_NAME

# 运行时记录按实例拆分，防止污染
RECORDS_DIR = PROFILE_DIR / "data/ai_records"
TEMP_DIR = RECORDS_DIR / "temp"

# 帮助图属实例产物，落实例数据目录，不与 data 按实例隔离冲突
HELP_IMAGE = PROFILE_DIR / "data/help.png"

# 日志按实例拆分，共用目录会互相污染且 GUI 打不开对应实例的记录
LOGS_DIR = PROFILE_DIR / "logs"
BOT_LOG = LOGS_DIR / "bot.log"
DEBUG_LOG = LOGS_DIR / "debug.log"

PERSONALITY_EXAMPLE = ASSETS_DIR / ASSET_PERSONA_EXAMPLE_NAME
