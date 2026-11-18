"""环境保留清单

- 五路依赖并成一份去重的保留清单，同名取先读到的那条 pin
- 同名被两处钉了不同版本时交出说明行，供同步动手前播报
"""

from finshin_sdk.domain import (
    ManifestKey,
    Platform,
    PluginFileName,
    StateKey,
    is_enabled,
)
from skin.messages import PluginMessage
from system.distributions import SDK_DISTRIBUTION, installed_version
from system.plugin_state import load_instance_enabled
from system.profile_env import INSTANCES_DIR
from system.tool_settings import DEVTOOLS_DECLARATION, declaration

from ..adapter_manifest import adapter_deps_union, installed_adapter_pins
from .deps_manifest import load_manifests, plugins_roots, top_package_name


def keep_union(exclude: Platform | None = None) -> list[str]:
    """全局保留清单

    - 核心依赖、接口包、适配器声明依赖、已装适配器包与全实例启用插件依赖并集
    - 同一只库只留一条，取各路顺序里先读到的那条 pin
    - 本实例刚保存的启用集已在盘上，并集即最新状态
    - 点名排除即不计那一平台适配器的声明与包
    """
    return _merge_keep(exclude)[0]


def keep_conflicts() -> list[str]:
    """同一只库被两处钉了不同版本时的说明行

    - 保留按各路顺序取先到的，报的是让开的那一条
    - 清单照旧能跑，这句只把谁让了谁摆到台面上
    """
    return _merge_keep()[1]


def dev_dependencies() -> list[str]:
    """读取开发工具清单

    - 只取钉了版本的条目，声明文件不在场返回空表
    - 仅供同步环境时保留已装工具
    """
    data = declaration(DEVTOOLS_DECLARATION)
    return [
        pin for pin in data.get("project", {}).get("dependencies", []) if "==" in pin
    ]


def _keep_sources(exclude: Platform | None = None) -> list[list[str]]:
    """按保留优先级排开的各路依赖"""
    return [
        _core_dependencies(),
        _installed_sdk_pin(),
        adapter_deps_union(exclude),
        installed_adapter_pins(exclude),
        _enabled_deps_union(),
    ]


def _installed_sdk_pin() -> list[str]:
    """已装接口包的 pin

    - 不在场不追加，避免 sync 顺带从索引强装
    """
    version = installed_version(SDK_DISTRIBUTION)
    return [f"{SDK_DISTRIBUTION}=={version}"] if version else []


def _core_dependencies() -> list[str]:
    """读取项目声明的核心依赖

    - 声明文件缺失时返回空表
    """
    data = declaration()
    return list(data.get("project", {}).get("dependencies", []))


def _merge_keep(
    exclude: Platform | None = None,
) -> tuple[list[str], list[str]]:
    """聚合保留清单与冲突说明"""
    kept: dict[str, str] = {}
    notes: list[str] = []
    for pin in (pin for source in _keep_sources(exclude) for pin in source):
        name = top_package_name(pin)
        if not name:
            continue
        winner = kept.setdefault(name, pin)
        if winner != pin:
            notes.append(
                PluginMessage.KEEP_CONFLICT.format(name=name, kept=winner, skipped=pin)
            )

    return list(kept.values()), notes


def _enabled_deps_union() -> list[str]:
    """汇总全部实例已启用插件的依赖并集"""
    return _enabled_field_union(ManifestKey.DEPS)


def _enabled_field_union(field: str) -> list[str]:
    """按清单字段汇总全实例的启用并集

    - 实例目录逐个子目录扫状态文件，目录不存在返回空表
    """
    items: list[str] = []
    if not INSTANCES_DIR.is_dir():
        return items

    manifests = load_manifests(plugins_roots())
    for path in sorted(INSTANCES_DIR.iterdir()):
        if not path.is_dir():
            continue
        enabled = load_instance_enabled(path / PluginFileName.STATE, StateKey.ENABLED)
        for manifest in manifests:
            if is_enabled(manifest[ManifestKey.NAME], enabled):
                items.extend(manifest[field])
    return items
