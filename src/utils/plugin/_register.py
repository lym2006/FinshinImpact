# src/utils/plugin/_register.py
"""插件注册表

- 按清单与实例启用集决定加载序列
- 实现路由注册与逐项结果上报
"""

import importlib
from typing import TYPE_CHECKING

from core.domain import PLUGINS_PKG, PluginFileName
from core.dto import PluginManifestDTO
from exceptions import PluginsMissingError

from ..paths import PROFILE_DIR
from ._manifest import enabled_manifests

if TYPE_CHECKING:
    from aiogram import Dispatcher

# 逐项报告：(插件名, 是否成功, 失败原因)
_PluginReport = list[tuple[str, bool, str]]


def register_routers(dispatcher: "Dispatcher") -> _PluginReport:
    """按启用序列注册插件

    - 返回逐项报告，未启用的插件不进报告
    - core 插件加载失败直接上抛，可选插件失败仅记原因
    - 全部失败抛 PluginsMissingError
    """
    report: _PluginReport = []
    success_count = 0

    for manifest in _resolve_plugins():
        plugin_name = manifest.name
        try:
            # 动态导入插件模块
            module = importlib.import_module(f"{PLUGINS_PKG}.{plugin_name}")

            # 检查插件是否导出了标准的 router 对象
            router = getattr(module, "router", None)
            if router is None:
                report.append(
                    (
                        plugin_name,
                        False,
                        "缺少 router 属性（检查 __init__.py）",
                    )
                )
                continue

            # 清除旧的父路由引用，允许重新附加到新 Dispatcher
            router._parent_router = None
            dispatcher.include_router(router)
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

    return report


def _resolve_plugins() -> list[PluginManifestDTO]:
    """计算本次注册序列

    - 与帮助聚合共用 enabled_manifests 取序列
    - 序列为空时走全失败分支抛 PluginsMissingError
    """
    return enabled_manifests(PROFILE_DIR / PluginFileName.STATE)
