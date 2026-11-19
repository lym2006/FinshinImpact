"""配置工具门面

- 检查、读写与校验出口
- 装配入口与段名出处
"""

from collections.abc import Sequence

from ..paths import CONFIG_FILE
from ._differ import compare_configs
from ._io import ConfigIO
from ._schema import build_schema
from ._validator import validate_types
from .models import AppConfigData, AppSchema, FieldErrors
from .sources import (
    ConfigPlan,
    ConfigSource,
    SourceKind,
    assemble,
    current_plan,
    section_name,
    use_plan,
)

__all__ = [
    # 装配与生命周期
    "ensure_config",
    "ConfigSource",
    "SourceKind",
    "section_name",
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
    "FieldErrors",
]


def _io() -> ConfigIO:
    """取得配置读写器

    - 每次调用按当前配置文件路径构造
    """
    return ConfigIO(CONFIG_FILE)


def _plan() -> ConfigPlan:
    """装配段表

    - 装配没发生即空表
    """
    return current_plan() or ConfigPlan(())


def ensure_config(sources: Sequence[ConfigSource]) -> None:
    """装配段表并确保配置文件存在

    - 文件不存在时按段表写默认值与说明
    - 文件已存在则不读内容、不改、不写盘
    - 必填项留空由本地校验报出，向导据此标红引导填写
    """
    plan = assemble(sources)
    use_plan(plan)
    if not CONFIG_FILE.exists():
        _io().save(plan.defaults(), notes=plan.notes())


def get_schema() -> AppSchema:
    """获取当前实例的 Schema 树"""
    return build_schema(_plan().sections)


def load_config() -> AppConfigData:
    """读取配置数据"""
    return _io().load()


def save_config(config_data: AppConfigData) -> None:
    """GUI 数据写回磁盘

    - 说明子表按交出模板重打
    """
    _io().save(config_data, notes=_plan().notes())
