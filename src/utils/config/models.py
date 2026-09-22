# src/utils/config/models.py
"""配置数据模型（内部实现）

- 定义值类型别名与校验规则枚举
"""

from dataclasses import dataclass, field

# ==================== 核心配置值类型 ====================

# 单个 TOML 配置值
ConfigValue = str | bool | float | list[str] | None

# ==================== 运行时配置数据结构 ====================

# 一个标签页
TabData = dict[str, ConfigValue]

# 完整 TOML 配置文件结构
AppConfigData = dict[str, TabData]


# ==================== 校验占位协议 ====================

# 前置项失败导致某项无法验证时的文案前缀（proxy 坏则 token 测不了）
PENDING_MARK = "暂未检测"

# 代理三级解析：配置地址 → 系统代理 → 直连（TUN 由 OS 层透明接管），
# 谁先连通谁生效；模式不落盘、GUI 不代填，全部交给启动校验与网络诊断
PROXY_FIELD = "proxy"

# ==================== UI Schema 结构契约 ====================


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


# 完整 UI 渲染结构树
AppSchema = list[TabSchema]
