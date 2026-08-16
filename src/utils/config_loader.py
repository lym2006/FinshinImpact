import logging
import sys
import tomllib

from .init_files import ensure_file_exists, merge_config
from .root_dir import ROOT_DIR

logger = logging.getLogger("Bot.Config")


def load_config():
    config_path = ROOT_DIR / "config.toml"
    example_path = ROOT_DIR / "config.example.toml"
    if not config_path.exists():
        if example_path.exists():
            logger.info("💡 未找到 config.toml，正在从模板自动创建...")
            ensure_file_exists("config.toml", "config.example.toml")
            logger.info("✅ config.toml 创建成功！")
            logger.error(
                "🛑 启动已暂停：请打开 config.toml 填入你的 Token 和 API 密钥后，重新启动机器人！"
            )
            sys.exit(1)
        else:
            logger.error(
                f"❌ 错误: 找不到配置文件 '{config_path}'\n"
                f"💡 请创建 config.toml 或确保 config.example.toml 存在"
            )
            sys.exit(1)
    config_updated = merge_config("config.toml", "config.example.toml")
    if config_updated:
        logger.error(
            "🛑 启动已暂停：请检查 config.toml 中新增的配置项，确认无误后重新启动机器人！"
        )
        sys.exit(1)
    try:
        with open(config_path, "rb") as f:
            config = tomllib.load(f)
        logger.info("✅ 配置导入成功")
        return config
    except Exception as e:
        logger.error(f"❌ 错误: 解析 config.toml 失败: {e}")
        sys.exit(1)


CONFIG = load_config()
