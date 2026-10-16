# src/utils/config/__init__.py
"""配置工具门面

- 提供检查、读写与校验出口
"""

from ..paths import CONFIG_FILE, PLATFORM
from ._differ import compare_configs
from ._io import ConfigIO
from ._schema import build_schema
from ._validator import validate_types
from ._writer import render_config
from .models import AppConfigData, AppSchema

__all__ = [
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
    # 数据结构
    "AppConfigData",
    "AppSchema",
]


def _io() -> ConfigIO:
    """取得配置读写器

    - 每次调用按当前 CONFIG_FILE 构造
    """
    return ConfigIO(CONFIG_FILE)


def ensure_config() -> None:
    """确保配置文件存在

    - 缺失则按平台段表生成初值后返回
    - 必填项留空由本地校验报出，向导据此标红引导填写
    """
    if CONFIG_FILE.exists():
        return
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(render_config(PLATFORM), encoding="utf-8")


def get_schema() -> AppSchema:
    """获取当前实例平台的 Schema 树"""
    return build_schema(PLATFORM)


def load_config() -> AppConfigData:
    """读取配置数据"""
    return _io().load()


def save_config(config_data: AppConfigData) -> None:
    """GUI 数据写回磁盘"""
    _io().save(config_data)
