# src/exceptions/_config.py
"""配置异常族

- 定义致命与可恢复两级配置异常
"""

from typing import Any

from ._base import BotError


class ConfigError(BotError):
    """配置系统异常基类"""


class ConfigMissingError(ConfigError):
    """可恢复的配置文件缺失异常"""


class ConfigTemplateMissingError(ConfigError):
    """配置模板缺失异常"""

    fatal = True


class ProfileMissingError(ConfigError):
    """实例身份缺失异常"""

    fatal = True


class ConfigInputError(ConfigError):
    """配置读取错误异常"""

    fatal = True


class ConfigOutputError(ConfigError):
    """配置写入错误异常"""

    fatal = True


class ConfigParseError(ConfigError):
    """配置解析错误异常"""

    fatal = True


class ConfigPathMissingError(ConfigError):
    """指定键的配置路径缺失异常"""

    def __init__(self, key_path: str, missing_key: str) -> None:
        self.key_path = key_path
        self.missing_key = missing_key
        super().__init__()


class ConfigAttrError(ConfigError):
    """配置取值异常

    - 类型不匹配
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
    ProfileMissingError: "实例身份缺失\n无法定位实例目录",
    ConfigInputError: "配置读取错误",
    ConfigOutputError: "配置写入错误",
    ConfigParseError: "配置模板解析错误",
    ConfigPathMissingError: "配置缺失：{key_path}\n找不到键：'{missing_key}'",
    ConfigAttrError: "配置项：{key_path}"
    "\n期望类型：{expected_type}"
    "\n实际类型：{actual_type}"
    "\n实际值：{actual_value}",
}
