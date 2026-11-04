# src/core/domain/config/_models.py
"""配置结构值对象

- 定义配置值类型别名
- 定义段名、键名与界面大类枚举
- 定义代理模式取值域
- 定义字段与段结构体
"""

from dataclasses import dataclass
from enum import StrEnum

from ..ids import ConfigPath

# 单个 TOML 配置值
ConfigValue = str | float | list[str] | None


class ConfigSection(StrEnum):
    """配置段名

    - 与 config.toml 顶层表名一一对应
    """

    # Telegram 专属段
    PROXY = "proxy"

    AI = "ai"
    CHORE = "chore"
    DATA = "data"


class ConfigGroup(StrEnum):
    """配置段所属的界面大类

    - 面板左侧大标签，一个大类下挂若干段页签
    """

    BOT = "bot"
    AI = "ai"


class ConfigKey(StrEnum):
    """配置键名

    - 与段内 TOML 键一一对应
    """

    # Telegram 专属键
    PROXY_MODE = "proxy_mode"
    PROXY = "proxy"

    API_KEY = "api_key"
    TEMPERATURE = "temperature"
    OWNER = "owner"
    TRIGGERS = "triggers"
    LOST_LINES = "lost_lines"
    RECORD_KEEP = "record_keep"
    WAITING = "waiting"

    def path(self, section: ConfigSection) -> ConfigPath:
        """拼点分路径"""
        return ConfigPath(f"{section}.{self}")


class ProxyMode(StrEnum):
    """代理模式协议串

    - 配置字段 proxy.proxy_mode 与校验编排共用
    - Telegram 专属取值域
    """

    AUTO = "auto"
    CFG = "cfg"
    SYS = "sys"
    DIRECT = "direct"


@dataclass(frozen=True, slots=True)
class FieldSpec:
    """单个配置项的结构定义

    - options 非空即枚举字段，取值为合法值元组
    - bounds 为闭区间，仅 float 字段生效
    """

    section: ConfigSection
    key: ConfigKey
    value_type: type
    default: ConfigValue
    required: bool = False
    options: tuple[str, ...] = ()
    bounds: tuple[float, float] | None = None

    @property
    def path(self) -> ConfigPath:
        """拼点分路径"""
        return ConfigPath(f"{self.section}.{self.key}")


@dataclass(frozen=True, slots=True)
class SectionSpec:
    """一个配置段的结构定义

    - fields 顺序即面板该页字段顺序
    - group 即面板左侧大标签
    """

    section: ConfigSection
    group: ConfigGroup
    fields: tuple[FieldSpec, ...]
