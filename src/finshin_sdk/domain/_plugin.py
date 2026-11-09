# src/finshin_sdk/domain/_plugin.py
"""插件对象

- 定义插件加载优先级、相关文件、清单键名与对象记号的词表
- 定义插件清单标量字段的类型、必填与默认
- 定义路由清单、常驻协程、任务处理与时机订阅的签名
- 定义平台侧的路由挂载口
- 定义插件之间抢命令名的判定
"""

from collections.abc import Awaitable, Callable, Coroutine, Sequence
from dataclasses import dataclass
from enum import IntEnum, StrEnum, auto
from typing import Any, Protocol

PLUGINS_PKG = "bundled"  # 插件树顶层包名，find_spec 与动态导入路径共用同值
INSTALLED_PLUGINS_NAME = "plugins_installed"  # 项目根下的外部插件目录，目录名即顶层包名

# 插件声明的无参常驻协程，随 Bot 服务起停
BackgroundLoop = Callable[[], Coroutine[Any, Any, None]]

# 路由谓词，只吃归一后的处理上下文，返回是否接管这条事件
RouteMatcher = Callable[..., Awaitable[bool]]

# 路由处理函数，首位按位置收本平台原始件且不许读它，归一事件与上下文都从 ctx 取
_PluginHandler = Callable[..., Awaitable[None]]

# 任务处理函数，只吃归一后的处理上下文，报错自行收干净再交回调度
ActionRun = Callable[..., Awaitable[None]]

# 时机订阅的处理函数，收平台召唤时交代的那一份能力
PluginTimingRun = Callable[..., Awaitable[None]]


class PlatformTiming(StrEnum):
    """平台会说出口的机会

    - 加新机会在这里加一名，不在插件入口基类上加方法
    - 名字只说平台发生了什么，不说插件该干什么
    """

    BEFORE_ENGINE_RUN = auto()
    IDENTITY_CHANGED = auto()

    # 校验通过即说出口，落盘排在随后由界面动手
    CONFIG_VERIFIED = auto()


@dataclass(frozen=True, slots=True)
class QueuedAction:
    """一条动作声明

    - 同一动作名只认最先交出来的那个
    """

    kind: str
    run: ActionRun


@dataclass(frozen=True, slots=True)
class MessageRoute:
    """一条路由声明

    - 谓词判真才进处理函数
    """

    predicate: RouteMatcher
    handler: _PluginHandler


@dataclass(frozen=True, slots=True)
class PluginTiming:
    """一条时机订阅

    - timing 决定什么时候轮到，run 收平台交代的那一份能力
    - 同一时机交多条即按交出的顺序跑
    """

    timing: PlatformTiming
    run: PluginTimingRun


class BasePlugin:
    """插件入口基类

    - 三只方法都可以不写，不写即没有那一类能力
    - 交出的清单按交出的顺序生效，本体不认识具体能力
    """

    def message_routes(self) -> tuple[MessageRoute, ...]:
        """来向消息的路由清单"""
        return ()

    def background_loops(self) -> tuple[BackgroundLoop, ...]:
        """随机器人起停的常驻循环"""
        return ()

    def queued_actions(self) -> tuple[QueuedAction, ...]:
        """可排队的动作清单"""
        return ()


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


def is_enabled(name: str, enabled: frozenset[str] | None) -> bool:
    """判定插件本次在场

    - 随包表里的插件恒在场
    - enabled 为 None 表示实例从未保存过选择，表外插件一律不在场
    """
    return name in BUNDLED_PLUGIN_PRIORITY or (enabled is not None and name in enabled)


@dataclass(frozen=True, slots=True)
class PluginClaim:
    """命令名抢占判定的一条插件记录

    - commands 是本插件清单声明的命令名，没声明即空
    """

    name: str
    commands: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CommandTaken:
    """一条被抢走的命令名与抢走它的插件"""

    cmd: str
    owner: str


def resolve_claims(
    claims: Sequence[PluginClaim],
    enabled: frozenset[str] | None,
) -> tuple[frozenset[str], dict[str, tuple[CommandTaken, ...]]]:
    """解开插件之间的命令名抢占

    - 回 (放行的插件名, 按插件名交出被抢走的命令名)，装载与面板共用这一份
    - 只有在场的插件拿走命令名，在场与否由 is_enabled 定
    - 一个命令名只有一只在场时它拿走，多只在场时随包件拿走
    - 同一命令名多只表外插件同时在场即整组作废，本次一起禁用且不记冲突
    - 不在场但命令名被拿走的照记冲突，面板据此禁掉勾选
    - 随包表里的插件恒放行也不记冲突，表内互抢归本体安排
    - 插件任一命令名被抢走即整只不放行，路由由插件整体交出，摘不掉单独一条
    """
    holders: dict[str, list[str]] = {}
    for claim in claims:
        if not is_enabled(claim.name, enabled):
            continue
        for cmd in claim.commands:
            holders.setdefault(cmd, []).append(claim.name)

    owners: dict[str, str] = {}
    voided: set[str] = set()
    for cmd, names in holders.items():
        bundled = [name for name in names if name in BUNDLED_PLUGIN_PRIORITY]
        if len(names) == 1 or bundled:
            owners[cmd] = bundled[0] if bundled else names[0]
            continue
        voided.update(names)

    allowed: set[str] = set()
    conflicts: dict[str, tuple[CommandTaken, ...]] = {}
    for claim in claims:
        if claim.name in BUNDLED_PLUGIN_PRIORITY:
            allowed.add(claim.name)
            continue
        taken = tuple(
            CommandTaken(cmd, owners[cmd])
            for cmd in claim.commands
            if owners.get(cmd, claim.name) != claim.name
        )
        if taken:
            conflicts[claim.name] = taken
        elif is_enabled(claim.name, enabled) and claim.name not in voided:
            allowed.add(claim.name)

    return frozenset(allowed), conflicts


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
