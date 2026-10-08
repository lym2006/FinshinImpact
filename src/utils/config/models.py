# src/utils/config/models.py
"""配置数据模型

- 定义值类型别名与校验规则枚举
"""

from dataclasses import dataclass, field

# 核心配置值类型

# 单个 TOML 配置值
ConfigValue = str | bool | float | list[str] | None

# 运行时配置数据结构
TabData = dict[str, ConfigValue]  # 一个标签页

# 完整 TOML 配置文件结构
AppConfigData = dict[str, TabData]


class PersonaKey:
    """人设配置键

    - 配置向导预览与 AI 人设组装必须取同一组键名
    - 成员存 TOML 短键名，点分路径由 path 派生
    """

    NAMESPACE: str = "chore"
    USE_FILE: str = "use_file"
    PERSONALITY: str = "personality"
    OWNER: str = "owner"

    @classmethod
    def path(cls, key: str) -> str:
        """拼点分路径"""
        return f"{cls.NAMESPACE}.{key}"


# 校验占位协议

# 前置项失败导致某项无法验证时的文案前缀（proxy 坏则 token 测不了）
PENDING_MARK = "暂未检测"

# 代理三级解析（配置→系统→直连）：模式不落盘、GUI 不代填，交给启动校验与诊断
PROXY_FIELD = "proxy"

# 必填项缺失或留空的校验文案
REQUIRED_MARK = "必填项未填写"

# 必填项点分路径清单：硬编码防用户改配置绕过，防模板占位假值当真值上屏
REQUIRED_KEYS: frozenset[str] = frozenset(
    {
        "ai.api_key",
        PersonaKey.path(PersonaKey.OWNER),
        "chore.triggers",
    }
)


def is_blank(value: object) -> bool:
    """必填项空值判定

    - 空白字符串与空列表视为未填写
    - 数值与布尔无空态：0 和 False 都是合法填写，不许误伤
    """
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, list):
        return not value
    return False


# UI Schema 结构契约
@dataclass
class FieldSchema:
    """单个配置项的 UI 属性"""

    key: str  # 对应 TOML 里的键名
    label: str  # 界面上显示的标题
    desc: str  # 鼠标悬停时的提示语
    default: ConfigValue  # 默认值


@dataclass
class TabSchema:
    """一个标签页的 UI 结构"""

    title: str  # Tab 标题
    namespace: str  # TOML 顶层键名
    fields: list[FieldSchema] = field(default_factory=list)


AppSchema = list[TabSchema]  # 完整 UI 渲染结构树
