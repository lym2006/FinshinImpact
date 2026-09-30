# src/utils/_config_manager.py
"""配置管理器（内部实现）

- 提供点分路径唯一读取入口
- 非必填缺键回退模板默认值，必填缺键维持抛错
"""

from copy import deepcopy
from typing import Any, TypeVar, cast, get_origin

from exceptions import ConfigAttrError, ConfigPathMissingError

from .config import AppConfigData, AppSchema, get_schema
from .config.models import REQUIRED_KEYS, ConfigValue

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
        """点路径读取并校验

        非必填键缺失取模板默认值：升级后旧配置缺新键也能直接跑。
        必填键缺失照抛，校验轮已负责标红引导填写。
        """
        keys = path.split(".")
        value: Any = self._config

        # 路径穿透
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            elif path in REQUIRED_KEYS:
                raise ConfigPathMissingError(path, key) from None
            else:
                value = self._template_default(path)
                break

        # 空值检查
        if value is None:
            raise ConfigAttrError(path, expected_type, None) from None

        if (  # 类型转换
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

    def _template_default(self, path: str) -> ConfigValue:
        """按点路径取模板默认值

        deepcopy 隔离：防调用方就地改写 schema 里的共享默认对象。
        模板也没有该字段属代码错误，照抛缺键。
        """
        ns, _, key = path.partition(".")
        for tab in self.schema:
            if tab.namespace != ns:
                continue
            for fld in tab.fields:
                if fld.key == key:
                    return deepcopy(fld.default)
        raise ConfigPathMissingError(path, key) from None


config_manager = ConfigManager()  # 全局单例
