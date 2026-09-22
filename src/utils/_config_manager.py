# src/utils/_config_manager.py
"""配置管理器（内部实现）

- 提供点分路径唯一读取入口
"""

from copy import deepcopy
from typing import Any, TypeVar, cast, get_origin

from exceptions import ConfigAttrError, ConfigPathMissingError

from .config import AppConfigData, AppSchema, get_schema

T = TypeVar("T")


class ConfigManager:
    """全局配置管理器"""

    def __init__(self) -> None:
        # 模板解析懒加载：缺模板时不炸导入链，GUI 可先起来再弹致命窗
        self._schema: AppSchema | None = None
        self._config: AppConfigData = {}

    @property
    def schema(self) -> AppSchema:
        if self._schema is None:
            self._schema = get_schema()
        return self._schema

    def load(self, config_data: AppConfigData) -> None:
        """全量加载/覆盖配置"""
        self._config = deepcopy(config_data)

    def get_all(self) -> AppConfigData:
        """获取全部配置"""
        return self._config

    def get(self, path: str, expected_type: type[T]) -> T:
        """点路径读取并校验"""
        keys = path.split(".")
        value: Any = self._config

        # 路径穿透
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                raise ConfigPathMissingError(path, key) from None

        # 空值检查
        if value is None:
            raise ConfigAttrError(path, expected_type, None) from None

        # 类型转换
        if (
            isinstance(value, int) and expected_type is float
        ):  # 所有数字全部转 float 类型
            value = float(value)
        if expected_type is bool and isinstance(value, str):
            # TOML 布尔在部分手改场景落成字符串：宽容归一
            value = value.strip().lower() in ("true", "1", "yes")
        if get_origin(expected_type) is list and isinstance(
            value, list
        ):  # 列表内全部转 str 类型
            value = [str(item) for item in value]

        # 提取泛型信息
        target_type = get_origin(expected_type) or expected_type

        # 校验外层类型
        if not isinstance(value, target_type):
            raise ConfigAttrError(path, expected_type, value) from None

        return cast(T, value)


# 全局单例
config_manager = ConfigManager()
