"""插件清单读取器

- 扫描插件目录聚合各插件自描述清单
- 读取实例状态文件并计算启用序列
- 外部根里名字撞上随包表的插件整份不放行
- 命令名被在场插件拿走的整只不放行
- 引导期另有一份只取最小字段集的精简实现
"""

import importlib.machinery
import importlib.util
from pathlib import Path
from typing import Any

from finshin_sdk.domain import (
    BUNDLED_PLUGIN_PRIORITY,
    INSTALLED_PLUGINS_NAME,
    INSTALLED_PLUGINS_PKG,
    MANIFEST_FIELDS,
    PLUGINS_PKG,
    CommandPriority,
    ManifestKey,
    PluginClaim,
    PluginFileName,
    StateKey,
    is_enabled,
    resolve_claims,
)
from finshin_sdk.dto import PluginManifestDTO
from system.module_mount import mount_module, mount_package
from system.profile_env import DECLARATION_FILE_NAME, ROOT_DIR
from system.toml_read import read_toml
from system.tool_settings import declared_dependencies

from ._manifest_help import read_help_sections

# 清单标量字段与期望类型，deps/assets 列表成员一律 str
_SCALAR_TYPES: dict[str, type] = {spec.key: spec.value_type for spec in MANIFEST_FIELDS}

# 清单必填项，缺任一拒收
_REQUIRED_KEYS = tuple(spec.key for spec in MANIFEST_FIELDS if spec.required)

# 插件根：目录与这棵树的顶层包名
_PluginRoot = tuple[Path, str]

# 外部插件代码所在的目录名
_CODE_STEM = "src"


def _bundled_dir() -> Path | None:
    """定位随包插件包目录

    - find_spec 只定位不执行模块代码，冻结包下路径随包走
    - 定位失败返回 None，由调用方处理
    """
    spec = importlib.util.find_spec(PLUGINS_PKG)
    if spec is None or not spec.submodule_search_locations:
        return None
    return Path(next(iter(spec.submodule_search_locations)))


def _installed_dir() -> Path:
    """定位外部插件挂载点"""
    return ROOT_DIR / INSTALLED_PLUGINS_NAME


def _plugins_roots() -> list[_PluginRoot]:
    """列出插件根，随包在前外部在后

    - 外部目录不存在即不进表
    """
    roots: list[_PluginRoot] = []

    bundled = _bundled_dir()
    if bundled is not None:
        roots.append((bundled, PLUGINS_PKG))

    installed = _installed_dir()
    if installed.is_dir():
        mount_package(INSTALLED_PLUGINS_PKG, installed)
        roots.append((installed, INSTALLED_PLUGINS_PKG))

    return roots


def _code_dir(plugin_dir: Path) -> Path:
    """插件代码所在那一层

    - 有 src 就认它，没有就认插件目录本身
    """
    code = plugin_dir / _CODE_STEM
    return code if code.is_dir() else plugin_dir


def _load_manifests(
    plugins_path: Path, pkg: str, mount_code: bool
) -> dict[str, PluginManifestDTO]:
    """扫描插件目录聚合清单

    - 只认含清单文件的直接子目录
    - 按目录名升序插入，dict 保序
    - 读取失败或字段非法的插件跳过
    """
    manifests: dict[str, PluginManifestDTO] = {}

    if not plugins_path.is_dir():
        return manifests

    for path in sorted(plugins_path.iterdir()):
        manifest = _read_manifest(path, path.name, pkg)
        if manifest is not None:
            if mount_code:
                code = _code_dir(path)
                if code != path:
                    mount_module(manifest.module, code)
            manifests[manifest.name] = manifest

    return manifests


def _read_manifest(dir_path: Path, dir_name: str, pkg: str) -> PluginManifestDTO | None:
    """读取单份插件清单并接上自家依赖表

    - 清单缺失或解析失败返回 None
    - 必填三项缺失、name 与目录名不符或类型错误则整份拒收
    - 外部那份的依赖表读不出即整份拒收，随包那份的库在根声明里
    - 未知键忽略，可选字段缺省用 DTO 默认值
    - 导入路径按所在根的顶层包名拼，清单不写这一行
    """
    data = read_toml(dir_path / PluginFileName.MANIFEST)
    if data is None:
        return None

    kwargs: dict[str, Any] = {}
    for key, expected in _SCALAR_TYPES.items():
        if key not in data:
            continue
        value = data[key]
        if not isinstance(value, expected):
            return None
        if isinstance(value, list):
            if not all(isinstance(item, str) for item in value):
                return None
            kwargs[key] = tuple(value)
        else:
            kwargs[key] = value

    if not all(k in kwargs for k in _REQUIRED_KEYS):
        return None
    if kwargs[ManifestKey.NAME] != dir_name:
        return None

    deps = _deps_of(dir_path, pkg)
    if deps is None:
        return None

    if raw_sections := data.get(ManifestKey.HELP):
        kwargs["help_section"] = read_help_sections(raw_sections, dir_name)

    return PluginManifestDTO(deps=deps, module=f"{pkg}.{dir_name}", **kwargs)


def _deps_of(plugin_dir: Path, pkg: str) -> tuple[str, ...] | None:
    """一只插件的库，随包那份按根声明算即空表

    - 外部那份交出 None 即自家声明的依赖表读不出，整份不认
    """
    if pkg == PLUGINS_PKG:
        return ()

    return declared_dependencies(plugin_dir / DECLARATION_FILE_NAME)


def _load_instance_enabled(state_path: Path) -> frozenset[str] | None:
    """读取实例启用集

    - 只取 enabled 键，随包插件恒启用与回落由 _resolve_enabled 处理
    - 文件不存在或解析失败返回 None，前者即实例从未保存过插件选择
    """
    data = read_toml(state_path)
    if data is None:
        return None

    return frozenset(str(name) for name in data.get(StateKey.ENABLED, []))


def _load_catalog(state_path: Path) -> str:
    """读取实例目录指纹

    - 缺失或损坏返回空串，与任何现算指纹都不等
    """
    data = read_toml(state_path)
    if data is None:
        return ""

    return str(data.get(StateKey.CATALOG, ""))


def _resolve_enabled(
    manifests: dict[str, PluginManifestDTO],
    enabled: frozenset[str] | None,
) -> list[PluginManifestDTO]:
    """计算启用插件序列

    - 在场与否由 is_enabled 定，随包表里的插件恒启用
    - 先按随包表定档，表外插件一律常规档，同档按 name 字典序
    """
    picked = [
        manifest
        for manifest in manifests.values()
        if is_enabled(manifest.name, enabled)
    ]
    return sorted(
        picked,
        key=lambda m: (
            BUNDLED_PLUGIN_PRIORITY.get(m.name, CommandPriority.NORMAL),
            m.name,
        ),
    )


def _declared_commands(manifest: PluginManifestDTO) -> tuple[str, ...]:
    """取清单声明的命令名"""
    return tuple(
        command.cmd for section in manifest.help_section for command in section.commands
    )


def enabled_manifests(state_path: Path) -> list[PluginManifestDTO]:
    """读取启用插件的清单序列

    - 注册表与帮助聚合共用本函数取序列
    - 一根目录都定位不到或无清单返回空列表
    - 外部根里名字撞上随包表的插件不进序列，改名单也不放行
    - 同名插件按根的顺序取先读到的，随包压住外部
    - 命令名被在场插件拿走的整只不进序列，互抢的多只表外插件一起不作数
    """
    manifests: dict[str, PluginManifestDTO] = {}
    for dir_path, pkg in _plugins_roots():
        for name, manifest in _load_manifests(
            dir_path, pkg, pkg != PLUGINS_PKG
        ).items():
            if pkg != PLUGINS_PKG and name in BUNDLED_PLUGIN_PRIORITY:
                continue
            manifests.setdefault(name, manifest)

    enabled = _load_instance_enabled(state_path)
    claims = [
        PluginClaim(name=manifest.name, commands=_declared_commands(manifest))
        for manifest in manifests.values()
    ]
    allowed, _ = resolve_claims(claims, enabled)

    return [
        manifest
        for manifest in _resolve_enabled(manifests, enabled)
        if manifest.name in allowed
    ]
