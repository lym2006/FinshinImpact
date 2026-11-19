"""配置管理器

- 按配置项身份读取配置
- 非必填缺键回退 schema 默认值，必填缺键维持抛错
"""

from copy import deepcopy
from typing import Any, TypeVar, cast, get_origin

from exceptions import ConfigAttrError, ConfigPathMissingError
from finshin_sdk.domain import ConfigPath

from .config import AppConfigData, AppSchema, get_schema, section_name
from .config.models import ConfigValue, TabData

T = TypeVar("T")


class _ConfigManager:
    """全局配置管理器"""

    def __init__(self) -> None:
        # schema 懒加载：缺配置时不炸导入链，GUI 可先起来再弹致命窗
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
        """获取全部配置

        - 交出副本，调用方就地改写不回渗到内存里那份
        """
        return deepcopy(self._config)

    def get(self, item: ConfigPath, expected_type: type[T]) -> T:
        """按配置项身份读取并校验

        - 盘上段名由来源串与段名拼出
        - 非必填键缺失取 schema 默认值
        - 必填键缺失直接抛错，由校验轮标红引导填写
        """
        section = section_name(item.source, item.section)
        values: TabData = self._config.get(section) or {}

        if item.key in values:
            value: Any = values[item.key]
        else:
            value = self._schema_default(item)

        if value is None:
            raise ConfigAttrError(item, expected_type, None) from None

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
            value = [str(element) for element in value]

        target_type = get_origin(expected_type) or expected_type

        if not isinstance(value, target_type):
            raise ConfigAttrError(item, expected_type, value) from None

        return cast(T, value)

    def _schema_default(self, item: ConfigPath) -> ConfigValue:
        """schema 默认值

        - 按来源、段与键定位字段
        """
        for tab in self.schema:
            if tab.group != item.source or tab.section_id != item.section:
                continue
            for fld in tab.fields:
                if fld.key != item.key:
                    continue
                if fld.required:
                    raise ConfigPathMissingError(item, item.key) from None

                # deepcopy 隔离：防调用方就地改写 schema 里的共享默认对象
                return deepcopy(fld.default)

        # schema 也没有该字段属代码错误，照抛缺键
        raise ConfigPathMissingError(item, item.key) from None


config_manager = _ConfigManager()  # 全局单例
