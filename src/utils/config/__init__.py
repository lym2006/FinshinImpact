# src/utils/config/__init__.py
"""配置工具门面

- 提供检查、读写与校验出口
"""

from exceptions import (
    ConfigMissingError,
    ConfigTemplateMissingError,
)

from ..init_files import CONFIG_EXAMPLE, CONFIG_FILE
from ._differ import compare_configs
from ._io import ConfigIO
from ._parser import ConfigParser
from ._validator import validate_types
from .models import (
    PENDING_MARK,
    PROXY_FIELD,
    AppConfigData,
    AppSchema,
)

# 底层组件实例化
_IO = ConfigIO(CONFIG_FILE)
_PARSER = ConfigParser(CONFIG_EXAMPLE)

__all__ = [
    # 占位标记（re-export 自 models）
    "PENDING_MARK",
    "PROXY_FIELD",
    # 核心生命周期控制
    "ensure_config",
    # 数据读写
    "get_schema",
    "load_config",
    "save_config",
    # 数据比对
    "compare_configs",
    # 类型校验
    "validate_types",
]

# ==================== 启动阶段 ====================


def _write_clean_config() -> None:
    """从模板生成纯数据配置

    注释只存模板，防 tomlkit 合并搅乱排版。
    """
    lines = CONFIG_EXAMPLE.read_text(encoding="utf-8").splitlines()
    kept: list[str] = []
    for line in lines:
        if line.lstrip().startswith("#"):
            continue
        # 压缩连续空行，保持段落间隔为一行
        if not line.strip() and (not kept or not kept[-1].strip()):
            continue
        kept.append(line)
    CONFIG_FILE.write_text("\n".join(kept) + "\n", encoding="utf-8")


def ensure_config() -> None:
    """确保配置文件存在"""
    if CONFIG_FILE.exists():
        return

    if CONFIG_EXAMPLE.exists():
        _write_clean_config()
        raise ConfigMissingError() from None

    raise ConfigTemplateMissingError() from None


# ==================== 数据读取与 UI 渲染 ====================


def get_schema() -> AppSchema:
    """获取 Schema 树"""
    return _PARSER.parse()


def load_config() -> AppConfigData:
    """读取配置数据"""
    return _IO.load()


# ==================== 数据保存 ====================


def save_config(config_data: AppConfigData) -> None:
    """GUI 数据写回磁盘"""
    _IO.save(config_data)
