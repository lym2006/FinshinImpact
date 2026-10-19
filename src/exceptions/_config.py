# src/exceptions/_config.py
"""配置异常族（内部实现）

- 定义致命与可恢复两级配置异常
"""

from typing import Any

from ._base import BotError


class ConfigError(BotError):
    """配置系统异常基类"""


class ConfigMissingError(ConfigError):
    """配置文件缺失异常（可恢复）"""


class ConfigTemplateMissingError(ConfigError):
    """配置模板缺失异常（致命）"""

    fatal = True


class ConfigInputError(ConfigError):
    """配置读取错误异常（致命）"""

    fatal = True


class ConfigOutputError(ConfigError):
    """配置写入错误异常（致命）"""

    fatal = True


class ConfigParseError(ConfigError):
    """配置解析错误异常（致命）"""

    fatal = True


class ConfigPathMissingError(ConfigError):
    """配置路径缺失，找不到指定的键"""

    def __init__(self, key_path: str, missing_key: str) -> None:
        self.key_path = key_path
        self.missing_key = missing_key
        super().__init__()


class ConfigAttrError(ConfigError):
    """配置取值异常

    类型不匹配
    """

    def __init__(
        self, key_path: str, expected_type: type, actual_value: Any = None
    ) -> None:
        self.key_path = key_path
        self.expected_type = expected_type.__name__
        self.actual_type = type(actual_value).__name__
        self.actual_value = actual_value
        super().__init__()


CONFIG_MAP = {
    ConfigMissingError: "缺少配置文件，自动打开面板填写",
    ConfigTemplateMissingError: "缺少配置模板，阻止启动",
    ConfigInputError: "配置读取错误",
    ConfigOutputError: "配置写入错误",
    ConfigParseError: "配置模板解析错误",
    ConfigPathMissingError: "\n配置缺失：{key_path}\n找不到键：'{missing_key}'",
    ConfigAttrError: "\n配置项：{key_path}"
    "\n期望类型：{expected_type}"
    "\n实际类型：{actual_type}"
    "\n实际值：{actual_value}",
}
