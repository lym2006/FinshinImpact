# src/core/domain/config/_models.py
"""配置结构值对象

- 定义配置值类型别名
- 定义段名与键名枚举
- 定义代理模式取值域
- 定义字段与段结构体
"""

from dataclasses import dataclass
from enum import StrEnum

from ..ids import ConfigPath

# 单个 TOML 配置值
ConfigValue = str | bool | float | list[str] | None


class ConfigSection(StrEnum):
    """配置段名

    - 与 config.toml 顶层表名一一对应
    """

    PROXY = "proxy"
    GLOBAL = "global"
    AI = "ai"
    CHORE = "chore"
    DATA = "data"


class ConfigKey(StrEnum):
    """配置键名

    - 与段内 TOML 键一一对应
    """

    PROXY_MODE = "proxy_mode"
    PROXY = "proxy"
    NETWORK_TIMEOUT = "network_timeout"
    API_KEY = "api_key"
    TEMPERATURE = "temperature"
    OWNER = "owner"
    TRIGGERS = "triggers"
    USE_FILE = "use_file"
    PERSONALITY = "personality"
    CLEARUP = "clearup"
    WAITING = "waiting"

    def path(self, section: ConfigSection) -> ConfigPath:
        """拼点分路径"""
        return ConfigPath(f"{section}.{self}")


class ProxyMode(StrEnum):
    """代理模式协议串

    - 配置字段 proxy.proxy_mode 与校验编排共用
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
    """

    section: ConfigSection
    fields: tuple[FieldSpec, ...]
