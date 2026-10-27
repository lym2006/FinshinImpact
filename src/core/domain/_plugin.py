# src/core/domain/_plugin.py
"""插件对象

- 定义插件加载优先级词表
- 定义插件相关文件名词表
- 定义插件数据契约的键名词表
- 定义插件清单标量字段的类型、必填与默认
- 定义插件路由清单、常驻协程与历史清理协程的签名
- 定义平台侧的路由挂载口
"""

from collections.abc import Awaitable, Callable, Coroutine
from dataclasses import dataclass
from enum import IntEnum, StrEnum
from typing import Any, Protocol

PLUGINS_PKG = "plugins"  # 插件树顶层包名，find_spec 与动态导入路径共用同值

# 插件声明的无参常驻协程，随 Bot 服务起停
PluginBackground = Callable[[], Coroutine[Any, Any, None]]

# 插件声明的无参历史清理协程，平台判定身份变更后调用
PluginReset = Callable[[], Coroutine[Any, Any, None]]

# 路由谓词，只吃归一后的处理上下文，返回是否接管这条事件
PluginPredicate = Callable[..., Awaitable[bool]]

# 路由处理函数，首位按位置收原始事件，ctx 按名注入
_PluginHandler = Callable[..., Awaitable[None]]


@dataclass(frozen=True, slots=True)
class PluginRoute:
    """一条路由声明

    - 谓词判真才进处理函数
    """

    predicate: PluginPredicate
    handler: _PluginHandler


@dataclass(frozen=True, slots=True)
class PluginSpec:
    """插件交平台装配的清单

    - routes 的顺序即匹配优先级
    - backgrounds 随 Bot 服务起停
    - history_reset 交出本插件的对话历史清理入口，不涉历史的插件留空
    """

    routes: tuple[PluginRoute, ...] = ()
    backgrounds: tuple[PluginBackground, ...] = ()
    history_reset: PluginReset | None = None


class RouteSink(Protocol):
    """平台引擎的路由挂载口

    - 注册表只交还编好的路由对象，不认它的类型与构造
    """

    def include_router(self, router: Any) -> Any:
        """挂上一份路由"""


class CommandPriority(IntEnum):
    """插件加载优先级

    - 数值越小越优先，同值按 name 字典序
    - 新插件一律取 NORMAL，禁止在现有档位之间插值
    """

    FIRST = 0  # help 独占
    NORMAL = 10  # 常规与新增默认
    LAST = 50  # AI 独占


class PluginFileName(StrEnum):
    """插件相关文件名

    - 文件名单源，禁止在别处重复定义
    """

    MANIFEST = "plugin.toml"  # 位于各插件目录，存插件自描述清单
    STATE = "plugins.toml"  # 位于实例目录，存启用集与 catalog 指纹


class ManifestKey(StrEnum):
    """插件清单键名

    - 与 plugin.toml 字段一一对应
    """

    NAME = "name"
    TITLE = "title"
    SUMMARY = "summary"
    CORE = "core"
    ORDER = "order"
    DEPS = "deps"
    ASSETS = "assets"
    HELP = "help"


class HelpKey(StrEnum):
    """帮助贡献键名

    - 段级与命令级共用
    """

    SECTION = "section"
    NOTE = "note"
    COMMANDS = "commands"
    CMD = "cmd"
    DESC = "desc"
    FLAGS = "flags"


class StateKey(StrEnum):
    """实例状态文件键名

    - 面板写侧与运行期读侧共用
    """

    ENABLED = "enabled"
    CATALOG = "catalog"


@dataclass(frozen=True, slots=True)
class ManifestFieldSpec:
    """插件清单标量字段规格

    - deps/assets 值类型为 list，成员一律 str
    - order 值类型为 int，取值须落在 CommandPriority 档位
    """

    key: ManifestKey
    value_type: type
    default: Any
    required: bool = False


MANIFEST_FIELDS: tuple[ManifestFieldSpec, ...] = (
    ManifestFieldSpec(ManifestKey.NAME, str, "", required=True),
    ManifestFieldSpec(ManifestKey.TITLE, str, "", required=True),
    ManifestFieldSpec(ManifestKey.SUMMARY, str, "", required=True),
    ManifestFieldSpec(ManifestKey.CORE, bool, False),
    ManifestFieldSpec(ManifestKey.ORDER, int, CommandPriority.NORMAL),
    ManifestFieldSpec(ManifestKey.DEPS, list, ()),
    ManifestFieldSpec(ManifestKey.ASSETS, list, ()),
)

# order 合法取值域，越界拒收
ORDER_TIERS = frozenset(CommandPriority)
