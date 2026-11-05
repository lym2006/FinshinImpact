# src/core/domain/_plugin.py
"""插件对象

- 定义插件加载优先级、相关文件、清单键名与对象记号的词表
- 定义插件清单标量字段的类型、必填与默认
- 定义路由清单、常驻协程、任务处理与时机订阅的签名
- 定义平台侧的路由挂载口
"""

from collections.abc import Awaitable, Callable, Coroutine
from dataclasses import dataclass
from enum import IntEnum, StrEnum, auto
from typing import Any, Protocol

from ._task import TaskKind

PLUGINS_PKG = "bundled"  # 插件树顶层包名，find_spec 与动态导入路径共用同值

# 插件声明的无参常驻协程，随 Bot 服务起停
PluginBackground = Callable[[], Coroutine[Any, Any, None]]

# 路由谓词，只吃归一后的处理上下文，返回是否接管这条事件
PluginPredicate = Callable[..., Awaitable[bool]]

# 路由处理函数，首位按位置收原始事件，ctx 按名注入
_PluginHandler = Callable[..., Awaitable[None]]

# 任务处理函数，只吃归一后的处理上下文，报错自行收干净再交回调度
TaskRun = Callable[..., Awaitable[None]]

# 时机订阅的处理函数，收平台召唤时交代的那一份能力
PluginTimingRun = Callable[..., Awaitable[None]]


class PlatformTiming(StrEnum):
    """平台会说出口的机会

    - 加新机会在这里加一名，不在 PluginSpec 上加字段
    - 名字只说平台发生了什么，不说插件该干什么
    """

    BEFORE_ENGINE_RUN = auto()
    IDENTITY_CHANGED = auto()

    # 校验通过即说出口，落盘排在随后由界面动手
    CONFIG_VERIFIED = auto()


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
class PluginTiming:
    """一条时机订阅

    - timing 决定什么时候轮到，run 收平台交代的那一份能力
    - 同一时机交多条即按交出的顺序跑
    """

    timing: PlatformTiming
    run: PluginTimingRun


@dataclass(frozen=True, slots=True)
class PluginSpec:
    """插件交平台装配的清单

    - routes 的先后即匹配优先级
    - backgrounds 随 Bot 服务起停
    - task_handlers 按任务类型派发
    - timings 交出本插件订阅的平台机会，没订阅即空
    """

    routes: tuple[PluginRoute, ...] = ()
    backgrounds: tuple[PluginBackground, ...] = ()
    task_handlers: tuple[TaskHandler, ...] = ()
    timings: tuple[PluginTiming, ...] = ()


class RouteSink(Protocol):
    """平台引擎的路由挂载口"""

    def include_router(self, router: Any) -> Any:
        """挂上一份路由"""


class CommandPriority(IntEnum):
    """插件加载优先级

    - 数值越小越优先，同值按名字典序
    """

    FIRST = 0  # 最先档
    NORMAL = 10  # 常规档，表外插件一律这档
    LAST = 50  # 最后档


# 随包插件的恒启用与加载档位，表外插件一律常规档
BUNDLED_PLUGIN_PRIORITY: dict[str, CommandPriority] = {
    "help": CommandPriority.FIRST,
    "grant": CommandPriority.NORMAL,
    "AI": CommandPriority.LAST,
}


class PluginFileName(StrEnum):
    """插件相关文件名"""

    MANIFEST = "plugin.toml"  # 位于各插件目录，存插件自描述清单
    STATE = "plugins.toml"  # 位于实例目录，存启用集与 catalog 指纹


class ManifestKey(StrEnum):
    """插件清单键名"""

    NAME = "name"
    TITLE = "title"
    SUMMARY = "summary"
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
    ARGS = "args"
    ROLE = "role"


class PluginMark(StrEnum):
    """插件交来的对象上挂的记号

    - 命令名挂在路由谓词上，权限档挂在处理函数上
    """

    COMMAND_NAME = "command_name"
    COMMAND_ROLE = "command_role"


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
    ManifestFieldSpec(ManifestKey.DEPS, list, ()),
    ManifestFieldSpec(ManifestKey.ASSETS, list, ()),
)
