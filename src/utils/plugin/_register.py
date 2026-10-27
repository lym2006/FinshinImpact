# src/utils/plugin/_register.py
"""插件注册表

- 按清单与实例启用集决定加载序列
- 实现路由注册、常驻协程与历史清理入口收集、逐项结果上报
- 插件只交路由清单，缺 spec 记失败
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
    RouteSink,
)
from core.dto import PluginManifestDTO
from exceptions import PluginsMissingError

from ..paths import PROFILE_DIR
from ._manifest import enabled_manifests

# 逐项报告：(插件名, 是否成功, 失败原因)
_PluginReport = list[tuple[str, bool, str]]

# 注册结果：逐项报告、待启动的常驻协程与待挂载的历史清理入口
_RegisterResult = tuple[
    _PluginReport, tuple[PluginBackground, ...], tuple[PluginReset, ...]
]

# 平台侧的清单编译器，注册表只按契约交还对象，不认它的构造
_RouteBuilder = Callable[[PluginSpec], Any]


def register_plugins(
    sink: RouteSink,
    build_router: _RouteBuilder,
) -> _RegisterResult:
    """按启用序列注册插件

    - sink 只被要求提供挂载路由这一个方法
    - build_router 由平台侧注入，把 PluginSpec 编成引擎要挂的对象
    - 返回逐项报告、全部插件声明的常驻协程与全部历史清理入口
    - 未启用的插件不进报告
    - core 插件加载失败直接上抛，可选插件失败仅记原因
    - 全部失败抛 PluginsMissingError
    """
    report: _PluginReport = []
    backgrounds: list[PluginBackground] = []
    resets: list[PluginReset] = []
    success_count = 0

    for manifest in _resolve_plugins():
        plugin_name = manifest.name
        try:
            # 动态导入插件模块
            module = importlib.import_module(f"{PLUGINS_PKG}.{plugin_name}")
            spec = cast(PluginSpec | None, getattr(module, "spec", None))

            if spec is None:
                report.append(
                    (plugin_name, False, "缺少 spec 属性（检查 __init__.py）")
                )
                continue

            declared = _checked_backgrounds(spec.backgrounds)
            sink.include_router(build_router(spec))
            backgrounds.extend(declared)
            if spec.history_reset is not None:
                resets.append(spec.history_reset)
            report.append((plugin_name, True, ""))
            success_count += 1

        except ModuleNotFoundError as e:
            if f"{PLUGINS_PKG}.{plugin_name}" in str(e):
                reason = "未找到（检查目录结构）"  # 插件本身不存在
            else:
                # 插件内部缺少依赖
                reason = f"内部依赖缺失: {e}"
            if manifest.core:
                raise
            report.append((plugin_name, False, reason))

        except Exception as e:
            if manifest.core:
                raise
            report.append((plugin_name, False, f"{type(e).__name__}: {e}"))

    # 如果所有插件都加载失败，抛出异常
    if success_count == 0:
        raise PluginsMissingError() from None

    return report, tuple(backgrounds), tuple(resets)


def _checked_backgrounds(declared: object) -> tuple[PluginBackground, ...]:
    """校验插件声明的常驻协程

    - 非列表或元组即判形态非法
    - 非可调用成员直接丢弃
    """
    if not isinstance(declared, (list, tuple)):
        raise TypeError("backgrounds 必须是可调用对象的列表或元组")
    return tuple(cast(PluginBackground, hook) for hook in declared if callable(hook))


def _resolve_plugins() -> list[PluginManifestDTO]:
    """计算本次注册序列

    - 与帮助聚合共用 enabled_manifests 取序列
    - 序列为空时走全失败分支抛 PluginsMissingError
    """
    return enabled_manifests(PROFILE_DIR / PluginFileName.STATE)
