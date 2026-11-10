# src/utils/plugin/_register.py
"""插件注册表

- 按清单与实例启用集决定加载序列
- 从插件模块里认那只入口类，实例化后收它交出的路由、循环、动作与时机
- 入口类缺失或多只、外部件伸手本体内部，都记失败并写明原因
- 清单声明的命令权限与实际拦截对不上即记失败
"""

import importlib
from types import ModuleType
from typing import Any, cast

from exceptions import (
    PluginDependencyError,
    PluginEntryError,
    PluginImportError,
    PluginLoadError,
    PluginMissingError,
    PluginRoleError,
    PluginsError,
    PluginsMissingError,
)
from finshin_sdk import (
    BackgroundLoop,
    BasePlugin,
    MessageRoute,
    MomentSubscription,
    PlatformMoment,
    QueuedAction,
    RouterBuilder,
)
from finshin_sdk.domain import (
    BUNDLED_PLUGIN_PRIORITY,
    CommandRole,
    MomentRun,
    PluginFileName,
    PluginMark,
    RouteSink,
    is_own_action,
)
from finshin_sdk.dto import PluginManifestDTO

from ..error_guard import guard
from ..logger import get_logger
from ..paths import PROFILE_DIR
from ._manifest import enabled_manifests
from ._scope import check_external_scope

_logger = get_logger("Plugin")

# 逐项报告：(插件清单, 失败异常)，成功那项异常记 None
_PluginReport = list[tuple[PluginManifestDTO, PluginsError | None]]

# 注册结果：逐项报告、待启动的常驻循环、动作清单、按时机归组的订阅
_RegisterResult = tuple[
    _PluginReport,
    tuple[BackgroundLoop, ...],
    tuple[QueuedAction, ...],
    dict[PlatformMoment, tuple[MomentRun, ...]],
]


def register_plugins(
    sink: RouteSink,
    build_router: RouterBuilder,
) -> _RegisterResult:
    """按启用序列注册插件

    - 交回逐项报告，以及全部插件交出的常驻循环、动作清单与按时机归组的订阅
    - 未启用的插件不进报告
    - 必装插件加载失败直接上抛，可选插件失败把异常记进报告
    - 全部插件加载失败整体上抛
    """
    report: _PluginReport = []
    backgrounds: list[BackgroundLoop] = []
    handlers: list[QueuedAction] = []
    platform_moments: dict[PlatformMoment, list[MomentRun]] = {}
    success_count = 0

    for manifest in _resolve_plugins():
        bundled = manifest.name in BUNDLED_PLUGIN_PRIORITY
        try:
            # 外部件先查引用范围，随包树里的由那只手自己放行
            check_external_scope(manifest)

            # 动态导入插件模块，再认模块里那一只入口类
            entry = _entry_class(manifest, importlib.import_module(manifest.module))
            plugin = entry()

            routes, loops, actions, subs = _collect(plugin, manifest)

            _check_roles(manifest, routes)
            sink.include_router(build_router(routes))
            backgrounds.extend(loops)
            handlers.extend(actions)
            for moment, runs in _grouped_moments(subs).items():
                for run in _checked_hooks(runs, f"platform_moments.{moment}"):
                    guarded = _guarded_moment(run, manifest.name, moment)
                    platform_moments.setdefault(moment, []).append(guarded)
            report.append((manifest, None))
            success_count += 1
            _log_receipt(manifest.name, routes, loops, actions, subs)

        except ModuleNotFoundError as e:
            # 插件本身不存在与插件内部缺依赖分开报，两者用户动作不同
            missing = manifest.module in str(e)
            error: PluginsError = (
                PluginMissingError() if missing else PluginDependencyError()
            )
            if bundled:
                raise
            report.append((manifest, error))

        except (PluginEntryError, PluginImportError, PluginRoleError) as e:
            if bundled:
                raise
            report.append((manifest, e))

        except Exception as e:
            if bundled:
                raise
            report.append((manifest, PluginLoadError(type(e).__name__)))

    if success_count == 0:
        raise PluginsMissingError() from None

    return (
        report,
        tuple(backgrounds),
        tuple(handlers),
        {moment: tuple(runs) for moment, runs in platform_moments.items()},
    )


def _entry_class(manifest: PluginManifestDTO, module: ModuleType) -> type[BasePlugin]:
    """取插件模块里那一只入口类

    - 只认模块自己定义的 BasePlugin 子类，从别处引进来的名字不算
    - 一只都没有或不止一只，都当场报错
    """
    entries = [
        value
        for value in vars(module).values()
        if isinstance(value, type)
        and issubclass(value, BasePlugin)
        and value.__module__ == module.__name__
    ]
    if not entries:
        raise PluginEntryError(f"{manifest.name}：模块里没有 BasePlugin 子类")
    if len(entries) > 1:
        names = "、".join(sorted(item.__name__ for item in entries))
        raise PluginEntryError(
            f"{manifest.name}：入口类有 {len(entries)} 只（{names}）"
        )
    return entries[0]


def _log_receipt(
    name: str,
    routes: tuple[MessageRoute, ...],
    loops: tuple[Any, ...],
    actions: tuple[QueuedAction, ...],
    subs: tuple[MomentSubscription, ...],
) -> None:
    """把这只插件实际交出多少东西落到调试日志"""
    _logger.debug(
        f"插件 {name} 交出：路由 {len(routes)} 条、循环 {len(loops)} 个、"
        f"动作 {len(actions)} 个、时机 {len(subs)} 个"
    )


def _collect(
    plugin: BasePlugin, manifest: PluginManifestDTO
) -> tuple[
    tuple[MessageRoute, ...],
    tuple[Any, ...],
    tuple[QueuedAction, ...],
    tuple[MomentSubscription, ...],
]:
    """收入口类交出的四样清单，形态不对当场报错"""
    return (
        _checked_routes(plugin.message_routes()),
        _checked_hooks(plugin.background_loops(), "background_loops"),
        _checked_actions(plugin.queued_actions(), manifest.name),
        plugin.platform_moments(),
    )


def _checked_routes(declared: object) -> tuple[MessageRoute, ...]:
    """校验路由清单

    - 不是路由声明的条目直接报错，装配期就出声
    """
    if not isinstance(declared, (list, tuple)):
        raise TypeError("message_routes 必须是路由声明的列表或元组")
    for item in declared:
        if not isinstance(item, MessageRoute):
            raise TypeError(f"message_routes 里混进了非路由声明的条目: {item!r}")
    return tuple(declared)


def _checked_actions(declared: object, plugin_name: str) -> tuple[QueuedAction, ...]:
    """校验插件交出的动作清单

    - 不是动作声明的条目直接报错，装配期就出声
    - 动作名前段必须等于本插件名，谁的动作号归谁
    """
    if not isinstance(declared, (list, tuple)):
        raise TypeError("queued_actions 必须是动作声明的列表或元组")
    checked: list[QueuedAction] = []
    for item in declared:
        if not isinstance(item, QueuedAction):
            raise TypeError(f"queued_actions 里混进了非动作声明的条目: {item!r}")
        if not is_own_action(item.kind, plugin_name):
            raise TypeError(f"动作名 {item.kind} 不属于 {plugin_name} 名下")
        checked.append(item)
    return tuple(checked)


def _grouped_moments(
    declared: object,
) -> dict[PlatformMoment, tuple[MomentRun, ...]]:
    """把插件交出的时机订阅按时机名归组

    - 不是时机订阅的条目直接报错，装配期就出声
    """
    if not isinstance(declared, (list, tuple)):
        raise TypeError("platform_moments 必须是时机订阅的列表或元组")
    grouped: dict[PlatformMoment, list[MomentRun]] = {}
    for item in declared:
        if not isinstance(item, MomentSubscription):
            raise TypeError(f"platform_moments 里混进了非时机订阅的条目: {item!r}")
        grouped.setdefault(item.moment, []).append(item.run)
    return {moment: tuple(runs) for moment, runs in grouped.items()}


def _report_moment(exc: Exception, stage: str) -> None:
    """时机件的报错只落调试日志，不外弹"""
    _logger.send_error(f"{stage}的件出错", exc)


def _guarded_moment(run: MomentRun, plugin: str, moment: PlatformMoment) -> MomentRun:
    """给插件交出的时机协程包一层兜底

    - 件里抛出的错落一行日志，带上插件名与时机名
    - 三条时机的派发处因此都不必各自兜
    """
    guarded = guard(f"插件 {plugin} 在时机 {moment}", _report_moment, catch_all=True)(
        run
    )
    return cast("MomentRun", guarded)


def _checked_hooks(declared: object, field: str) -> tuple[Any, ...]:
    """校验插件声明的协程清单"""
    if not isinstance(declared, (list, tuple)):
        raise TypeError(f"{field} 必须是可调用对象的列表或元组")
    return tuple(hook for hook in declared if callable(hook))


def _resolve_plugins() -> list[PluginManifestDTO]:
    """计算本次注册序列"""
    return enabled_manifests(PROFILE_DIR / PluginFileName.STATE)


def _check_roles(manifest: PluginManifestDTO, routes: tuple[MessageRoute, ...]) -> None:
    """校验清单声明的命令权限与实际拦截一致

    - 清单写了要什么档，路由上必须有同档守卫
    - 清单写用户档的命令，路由上不带守卫
    """
    guarded = _guarded_roles(routes)
    for section in manifest.help_section:
        for command in section.commands:
            if guarded.get(command.cmd, CommandRole.MEMBER) != command.role:
                raise PluginRoleError(command.cmd)


def _guarded_roles(routes: tuple[MessageRoute, ...]) -> dict[str, CommandRole]:
    """取出路由上认得的命令名与守卫档位

    - 命令名读自谓词，守卫档位读自处理函数
    - 两者缺任一的条目不进表
    """
    guarded: dict[str, CommandRole] = {}
    for route in routes:
        name = getattr(route.predicate, PluginMark.COMMAND_NAME, None)
        limit = getattr(route.handler, PluginMark.COMMAND_ROLE, None)
        if isinstance(name, str) and isinstance(limit, CommandRole):
            guarded[name] = limit
    return guarded
