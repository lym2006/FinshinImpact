# src/utils/config_loader.py
"""
全局配置加载工具

提供：
- 配置文件自动创建与合并
- 全局配置解析与导出
"""

import logging
import tomllib
from typing import Any

from .exceptions import ConfigError
from .init_files import ensure_file_exists
from .root_dir import ROOT_DIR

logger = logging.getLogger("Bot.Config")


# ==================== 1. 内部辅助函数 ====================
def _merge_config(config_path: str, example_path: str) -> bool:
    """合并配置文件，将 example 中的新增字段同步到 config"""
    config = ROOT_DIR / config_path
    example = ROOT_DIR / example_path

    if not example.exists() or not config.exists():
        return False

    try:
        with open(example, "rb") as f:
            example_data = tomllib.load(f)
        with open(config, "rb") as f:
            config_data = tomllib.load(f)

        missing_keys = []

        def _merge_dicts(base, update, path="") -> None:
            """递归合并字典"""
            for key, value in update.items():
                current_path = f"{path}.{key}" if path else key
                if key not in base:
                    base[key] = value
                    missing_keys.append(current_path)
                elif isinstance(value, dict) and isinstance(base.get(key), dict):
                    _merge_dicts(base[key], value, current_path)

        _merge_dicts(config_data, example_data)

        if missing_keys:
            # 延迟导入 tomlkit
            import tomlkit

            with open(config, "w", encoding="utf-8") as f:
                tomlkit.dump(config_data, f)

            logger.warning("🆕 检测到以下新增配置项，已自动合并到 config.toml：")
            for key in missing_keys:
                logger.warning(f"  - {key}")
            return True

        return False

    except Exception as e:
        logger.error(f"❌ 错误: 检查配置更新时发生异常: {e}")
        return False


# ==================== 2. 核心配置加载 ====================
def _load_config() -> dict[str, Any]:
    """加载并解析全局配置文件"""
    config_path = ROOT_DIR / "config.toml"
    example_path = ROOT_DIR / "config.example.toml"

    # 1. 检查配置文件是否存在
    if not config_path.exists():
        if example_path.exists():
            logger.info("💡 未找到 config.toml，正在从模板自动创建...")
            ensure_file_exists("config.toml", "config.example.toml")
            logger.info("✅ config.toml 创建成功！")
            logger.error(
                "🛑 启动已暂停：请打开 config.toml 填入你的 Token 和 API 密钥后，重新启动机器人！"
            )
            raise ConfigError() from None
        else:
            logger.error(
                f"❌ 错误: 找不到配置文件 '{config_path}'\n"
                f"💡 请创建 config.toml 或确保 config.example.toml 存在"
            )
            raise ConfigError() from None

    # 2. 检查是否有新增配置项需要合并
    config_updated = _merge_config("config.toml", "config.example.toml")
    if config_updated:
        logger.error(
            "🛑 启动已暂停：请检查 config.toml 中新增的配置项，确认无误后重新启动机器人！"
        )
        raise ConfigError() from None

    # 3. 解析配置文件
    try:
        with open(config_path, "rb") as f:
            config = tomllib.load(f)
        logger.info("✅ 配置导入成功")
        return config
    except Exception as e:
        logger.error(f"❌ 错误: 解析 config.toml 失败: {e}")
        raise ConfigError() from None


CONFIG = _load_config()
