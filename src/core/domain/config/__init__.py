# src/core/domain/config/__init__.py
"""配置结构门面

- 代发配置值类型、段与键枚举、字段与段结构体
- 代发按平台拼装的段全表
"""

from ._models import (
    ConfigKey,
    ConfigSection,
    ConfigValue,
    FieldSpec,
    ProxyMode,
    SectionSpec,
)
from ._table import SECTIONS_BY_PLATFORM

__all__ = [
    # 值类型
    "ConfigValue",
    # 段与键
    "ConfigSection",
    "ConfigKey",
    # 代理模式取值域
    "ProxyMode",
    # 结构体
    "FieldSpec",
    "SectionSpec",
    # 平台段全表
    "SECTIONS_BY_PLATFORM",
]
