"""配置数据模型

- 定义运行期配置数据结构别名
- 定义界面渲染用的字段与页签结构体
"""

from dataclasses import dataclass, field

from finshin_sdk.domain import ConfigKey, ConfigPath, ConfigSection, ConfigValue

# 一个标签页的键值表，键为配置键名
TabData = dict[str, ConfigValue]

# 完整 TOML 配置文件结构，段名为带来源前缀的点分串
AppConfigData = dict[str, TabData]

# 配置校验错误表：键为出错字段，值为提示文案
FieldErrors = dict[ConfigPath | str, str]

# 单段说明子表，键名与该段下的值键同名
SectionNotes = dict[ConfigKey, str]

# 段名到说明子表，装配器每次按交出模板覆盖
NotesBySection = dict[str, SectionNotes]


def is_blank(value: object) -> bool:
    """必填项空值判定

    - 空白字符串与空列表视为未填写
    - 数值无空态，0 是合法填写
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
    """一个标签页的 UI 结构

    - group 与 group_title 定左侧大类，同大类的页并在上排页签里
    """

    title: str
    section: str  # 带来源前缀的点分段名，改名波及面板按段判定处
    group: str  # 左侧大类标识，值为来源身份串
    group_title: str  # 大类标题，随来源声明交出
    section_id: ConfigSection  # 本页字段所属枚举段名
    fields: list[FieldSchema] = field(default_factory=list)

    def path_of(self, field: FieldSchema) -> ConfigPath:
        """字段在本来源下的完整身份"""
        return ConfigPath(source=self.group, section=self.section_id, key=field.key)


AppSchema = list[TabSchema]  # 完整 UI 渲染结构树
