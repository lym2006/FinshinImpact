import logging
import tomllib

from .root_dir import ROOT_DIR

logger = logging.getLogger("Bot.Init")


def ensure_file_exists(target_path: str, template_path: str | None = None):
    target = ROOT_DIR / target_path
    if target.exists():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    if template_path and (ROOT_DIR / template_path).exists():
        target.write_bytes((ROOT_DIR / template_path).read_bytes())
        logger.info(f"[初始化] 已从模板创建: {target}")
    else:
        target.touch()
        logger.info(f"[初始化] 已创建空文件: {target}")


def merge_config(config_path: str, example_path: str) -> bool:
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

        def merge_dicts(base, update, path=""):
            for key, value in update.items():
                current_path = f"{path}.{key}" if path else key
                if key not in base:
                    base[key] = value
                    missing_keys.append(current_path)
                elif isinstance(value, dict) and isinstance(base.get(key), dict):
                    merge_dicts(base[key], value, current_path)

        merge_dicts(config_data, example_data)
        if missing_keys:
            import tomlkit

            with open(config, "w", encoding="utf-8") as f:
                tomlkit.dump(config_data, f)
            logger.warning(
                "[配置更新] 检测到以下新增配置项，已自动合并到 config.toml："
            )
            for key in missing_keys:
                logger.warning(f"  - {key}")
            return True
        return False
    except Exception as e:
        logger.error(f"❌ 错误: 检查配置更新时发生异常: {e}")
        return False


def init_project_files():
    logger.info("[初始化] 开始检查项目必要文件...")
    ensure_file_exists("assets/blacklist.txt")
    ensure_file_exists("src/plugins/AI/record/black.txt")
    logger.info("[初始化] 文件检查与初始化完成。")
