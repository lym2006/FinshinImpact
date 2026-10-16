# src/core/domain/config/__init__.py
"""配置结构门面

- 代发配置值类型、段与键枚举、字段与页签结构体
- 代发按平台拼装的段全表
"""

from ._models import (
    ConfigKey,
    ConfigNamespace,
    ConfigValue,
    FieldSpec,
    ProxyMode,
    TabSpec,
)
from ._table import TABS_BY_PLATFORM

__all__ = [
    # 值类型
    "ConfigValue",
    # 段与键
    "ConfigNamespace",
    "ConfigKey",
    # 代理模式取值域
    "ProxyMode",
    # 结构体
    "FieldSpec",
    "TabSpec",
    # 平台段全表
    "TABS_BY_PLATFORM",
]
