import sys
import tomllib
import logging
from pathlib import Path

logger=logging.getLogger("Bot.Config.Setup")

def get_project_root():
    return Path(__file__).resolve().parent.parent

def load_config(): 
    root_dir=get_project_root()
    config_path=root_dir/"config.toml"
    if not config_path.exists():
        logger.error(f"❌ 错误: 找不到配置文件 '{config_path}'\n💡 请创建 src/config.toml")
        sys.exit(1)
    try:
        with open(config_path,"rb") as f:
            config=tomllib.load(f)
        logger.info(f"✅ 配置导入成功")
        return config
    except Exception as e:
        logger.error(f"❌ 错误: 解析 config.toml 失败: {e}")
        sys.exit(1)

CONFIG=load_config()