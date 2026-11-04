# src/utils/plugin/_register.py
"""插件注册表

- 按清单与实例启用集决定加载序列
- 收集各插件交来的路由、常驻协程、任务处理与时机订阅，逐项上报加载结果
- 插件不交路由清单即记失败
- 清单声明的命令权限与实际拦截对不上即记失败
"""

import importlib
from collections.abc import Callable
from typing import Any, cast

from core.domain import (
    PLUGINS_PKG,
    CommandRole,
    PlatformTiming,
    PluginBackground,
    PluginFileName,
    PluginMark,
    PluginRoute,
    PluginSpec,
    PluginTiming,
    PluginTimingRun,
    RouteSink,
    TaskHandler,
)
from core.dto import PluginManifestDTO
from exceptions import (
    PluginDependencyError,
    PluginLoadError,
    PluginMissingError,
    PluginRoleError,
    PluginsError,
    PluginsMissingError,
    PluginSpecError,
)

from ..paths import PROFILE_DIR
from ._manifest import enabled_manifests

# 逐项报告：(插件名, 失败异常)，成功那项异常记 None
_PluginReport = list[tuple[str, PluginsError | None]]

# 注册结果：逐项报告、待启动的常驻协程、任务处理清单、按时机归组的订阅
_RegisterResult = tuple[
    _PluginReport,
    tuple[PluginBackground, ...],
    tuple[TaskHandler, ...],
    dict[PlatformTiming, tuple[PluginTimingRun, ...]],
]

# 平台侧的清单编译器，由装配层注入
_RouteBuilder = Callable[[PluginSpec], Any]


def register_plugins(
    sink: RouteSink,
    build_router: _RouteBuilder,
) -> _RegisterResult:
    """按启用序列注册插件

    - 交回逐项报告，以及全部插件声明的常驻协程、任务处理清单与按时机归组的订阅
    - 未启用的插件不进报告
    - 必装插件加载失败直接上抛，可选插件失败把异常记进报告
    - 全部插件加载失败整体上抛
    """
    report: _PluginReport = []
    backgrounds: list[PluginBackground] = []
    handlers: list[TaskHandler] = []
    timings: dict[PlatformTiming, list[PluginTimingRun]] = {}
    success_count = 0

    for manifest in _resolve_plugins():
        plugin_name = manifest.name
        try:
            # 动态导入插件模块
            module = importlib.import_module(f"{PLUGINS_PKG}.{plugin_name}")
            spec = cast(PluginSpec | None, getattr(module, "spec", None))

            if spec is None:
                report.append((plugin_name, PluginSpecError()))
                continue

            _check_roles(manifest, spec)
            declared = _checked_hooks(spec.backgrounds, "backgrounds")
            sink.include_router(build_router(spec))
            backgrounds.extend(declared)
            handlers.extend(spec.task_handlers)
            for timing, runs in _grouped_timings(spec.timings).items():
                for run in _checked_hooks(runs, f"timings.{timing}"):
                    timings.setdefault(timing, []).append(run)
            report.append((plugin_name, None))
            success_count += 1

        except ModuleNotFoundError as e:
            # 插件本身不存在与插件内部缺依赖分开报，两者用户动作不同
            missing = f"{PLUGINS_PKG}.{plugin_name}" in str(e)
            error: PluginsError = (
                PluginMissingError() if missing else PluginDependencyError()
            )
            if manifest.core:
                raise
            report.append((plugin_name, error))

        except PluginRoleError as e:
            if manifest.core:
                raise
            report.append((plugin_name, e))

        except Exception as e:
            if manifest.core:
                raise
            report.append((plugin_name, PluginLoadError(type(e).__name__)))

    if success_count == 0:
        raise PluginsMissingError() from None

    return (
        report,
        tuple(backgrounds),
        tuple(handlers),
        {timing: tuple(runs) for timing, runs in timings.items()},
    )


def _grouped_timings(
    declared: object,
) -> dict[PlatformTiming, tuple[PluginTimingRun, ...]]:
    """把插件交出的时机订阅按时机名归组

    - 不是时机订阅的条目直接报错，装配期就出声
    """
    if not isinstance(declared, (list, tuple)):
        raise TypeError("timings 必须是时机订阅的列表或元组")
    grouped: dict[PlatformTiming, list[PluginTimingRun]] = {}
    for item in declared:
        if not isinstance(item, PluginTiming):
            raise TypeError(f"timings 里混进了非时机订阅的条目: {item!r}")
        grouped.setdefault(item.timing, []).append(item.run)
    return {timing: tuple(runs) for timing, runs in grouped.items()}


def _checked_hooks(declared: object, field: str) -> tuple[Any, ...]:
    """校验插件声明的协程清单"""
    if not isinstance(declared, (list, tuple)):
        raise TypeError(f"{field} 必须是可调用对象的列表或元组")
    return tuple(hook for hook in declared if callable(hook))


def _resolve_plugins() -> list[PluginManifestDTO]:
    """计算本次注册序列"""
    return enabled_manifests(PROFILE_DIR / PluginFileName.STATE)


def _check_roles(manifest: PluginManifestDTO, spec: PluginSpec) -> None:
    """校验清单声明的命令权限与实际拦截一致

    - 清单写了要什么档，路由上必须有同档守卫
    - 清单写用户档的命令，路由上不带守卫
    """
    guarded = _guarded_roles(spec.routes)
    for section in manifest.help_section:
        for command in section.commands:
            if guarded.get(command.cmd, CommandRole.MEMBER) != command.role:
                raise PluginRoleError(command.cmd)


def _guarded_roles(routes: tuple[PluginRoute, ...]) -> dict[str, CommandRole]:
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
