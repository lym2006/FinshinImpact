# src/core/domain/_plugin.py
"""插件对象

- 定义插件加载优先级、相关文件与清单键名的词表
- 定义插件清单标量字段的类型、必填与默认
- 定义路由清单、常驻协程与各类入口的签名
- 定义平台侧的路由挂载口
"""

from collections.abc import Awaitable, Callable, Coroutine
from dataclasses import dataclass
from enum import IntEnum, StrEnum
from typing import Any, Protocol

from ._task import TaskKind

PLUGINS_PKG = "plugins"  # 插件树顶层包名，find_spec 与动态导入路径共用同值

# 插件声明的无参常驻协程，随 Bot 服务起停
PluginBackground = Callable[[], Coroutine[Any, Any, None]]

# 插件声明的无参历史清理协程，平台判定身份变更后调用
PluginReset = Callable[[], Coroutine[Any, Any, None]]

# 路由谓词，只吃归一后的处理上下文，返回是否接管这条事件
PluginPredicate = Callable[..., Awaitable[bool]]

# 路由处理函数，首位按位置收原始事件，ctx 按名注入
_PluginHandler = Callable[..., Awaitable[None]]

# 任务处理函数，只吃归一后的处理上下文，报错自行收干净再交回调度
TaskRun = Callable[..., Awaitable[None]]

# 启动交代函数，只吃外发端口，引擎起来后随轮询开跑前调用一次
PluginStartup = Callable[..., Awaitable[None]]


@dataclass(frozen=True, slots=True)
class TaskHandler:
    """一条任务处理声明

    - 同一类型只认最先交出来的那个
    """

    kind: TaskKind
    run: TaskRun


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

    - 路由的先后即匹配优先级
    - 不涉历史、不排队的插件对应条目留空
    """

    routes: tuple[PluginRoute, ...] = ()
    backgrounds: tuple[PluginBackground, ...] = ()
    history_reset: PluginReset | None = None
    task_handlers: tuple[TaskHandler, ...] = ()
    startups: tuple[PluginStartup, ...] = ()


class RouteSink(Protocol):
    """平台引擎的路由挂载口"""

    def include_router(self, router: Any) -> Any:
        """挂上一份路由"""


class CommandPriority(IntEnum):
    """插件加载优先级

    - 数值越小越优先，同值按名字典序
    """

    FIRST = 0  # help 独占
    NORMAL = 10  # 常规与新增默认
    LAST = 50  # AI 独占


class PluginFileName(StrEnum):
    """插件相关文件名"""

    MANIFEST = "plugin.toml"  # 位于各插件目录，存插件自描述清单
    STATE = "plugins.toml"  # 位于实例目录，存启用集与 catalog 指纹


class ManifestKey(StrEnum):
    """插件清单键名"""

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
    """插件清单标量字段规格"""

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
