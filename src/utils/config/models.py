# src/utils/config/models.py
"""配置数据模型

- 定义运行期配置数据结构别名
- 定义界面渲染用的字段与页签结构体
"""

from dataclasses import dataclass, field

from core.domain import ConfigKey, ConfigSection, ConfigValue

# 运行时配置数据结构
TabData = dict[str, ConfigValue]  # 一个标签页

# 完整 TOML 配置文件结构
AppConfigData = dict[str, TabData]

# 配置校验错误表：键为出错字段，值为提示文案
FieldErrors = dict[ConfigKey, str]


def is_blank(value: object) -> bool:
    """必填项空值判定

    - 空白字符串与空列表视为未填写
    - 数值与布尔无空态，0 和 False 都是合法填写
    """
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, list):
        return not value
    return False


@dataclass
class FieldSchema:
    """单个配置项的 UI 属性

    - key 为配置键枚举
    - options 非空即枚举字段，每项为「值 文案」对
    - bounds 为闭区间，仅 float 字段生效
    """

    key: ConfigKey
    label: str
    desc: str
    default: ConfigValue
    value_type: type
    options: tuple[tuple[str, str], ...] = ()
    required: bool = False
    bounds: tuple[float, float] | None = None


@dataclass
class TabSchema:
    """一个标签页的 UI 结构"""

    title: str  # Tab 标题
    section: ConfigSection  # TOML 顶层键名
    fields: list[FieldSchema] = field(default_factory=list)


AppSchema = list[TabSchema]  # 完整 UI 渲染结构树
