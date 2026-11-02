# src/utils/plugin/_register.py
"""插件注册表

- 按清单与实例启用集决定加载序列
- 收集各插件交来的路由、常驻协程与各类入口，逐项上报加载结果
- 插件不交路由清单即记失败
"""

import importlib
from collections.abc import Callable
from typing import Any, cast

from core.domain import (
    PLUGINS_PKG,
    PluginBackground,
    PluginFileName,
    PluginReset,
    PluginSpec,
    PluginStartup,
    RouteSink,
    TaskHandler,
)
from core.dto import PluginManifestDTO
from exceptions import (
    PluginDependencyError,
    PluginLoadError,
    PluginMissingError,
    PluginsError,
    PluginsMissingError,
    PluginSpecError,
)

from ..paths import PROFILE_DIR
from ._manifest import enabled_manifests

# 逐项报告：(插件名, 失败异常)，成功那项异常记 None
_PluginReport = list[tuple[str, PluginsError | None]]

# 注册结果：逐项报告、待启动的常驻协程、待挂载的历史清理入口、任务处理清单与启动交代协程
_RegisterResult = tuple[
    _PluginReport,
    tuple[PluginBackground, ...],
    tuple[PluginReset, ...],
    tuple[TaskHandler, ...],
    tuple[PluginStartup, ...],
]

# 平台侧的清单编译器，由装配层注入
_RouteBuilder = Callable[[PluginSpec], Any]


def register_plugins(
    sink: RouteSink,
    build_router: _RouteBuilder,
) -> _RegisterResult:
    """按启用序列注册插件

    - 交回逐项报告，以及全部插件声明的常驻协程、清理入口、任务处理清单与启动交代入口
    - 未启用的插件不进报告
    - 必装插件加载失败直接上抛，可选插件失败把异常记进报告
    - 全部插件加载失败整体上抛
    """
    report: _PluginReport = []
    backgrounds: list[PluginBackground] = []
    resets: list[PluginReset] = []
    handlers: list[TaskHandler] = []
    startups: list[PluginStartup] = []
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

            declared = _checked_hooks(spec.backgrounds, "backgrounds")
            sink.include_router(build_router(spec))
            backgrounds.extend(declared)
            handlers.extend(spec.task_handlers)
            startups.extend(_checked_hooks(spec.startups, "startups"))
            if spec.history_reset is not None:
                resets.append(spec.history_reset)
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

        except Exception as e:
            if manifest.core:
                raise
            report.append((plugin_name, PluginLoadError(type(e).__name__)))

    if success_count == 0:
        raise PluginsMissingError() from None

    return report, tuple(backgrounds), tuple(resets), tuple(handlers), tuple(startups)


def _checked_hooks(declared: object, field: str) -> tuple[Any, ...]:
    """校验插件声明的协程清单"""
    if not isinstance(declared, (list, tuple)):
        raise TypeError(f"{field} 必须是可调用对象的列表或元组")
    return tuple(hook for hook in declared if callable(hook))


def _resolve_plugins() -> list[PluginManifestDTO]:
    """计算本次注册序列"""
    return enabled_manifests(PROFILE_DIR / PluginFileName.STATE)
