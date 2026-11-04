# src/utils/plugin/_manifest.py
"""插件清单读取器

- 扫描插件目录聚合各插件自描述清单
- 读取实例状态文件并计算启用序列
- 引导期另有一份只取最小字段集的精简实现
"""

import importlib.util
import tomllib
from pathlib import Path
from typing import Any

from core.domain import (
    CORE_PLUGIN_PRIORITY,
    MANIFEST_FIELDS,
    PLUGINS_PKG,
    CommandPriority,
    ManifestKey,
    PluginFileName,
    StateKey,
)
from core.dto import PluginManifestDTO

from ._manifest_help import read_help_sections

# 清单标量字段与期望类型，deps/assets 列表成员一律 str
_SCALAR_TYPES: dict[str, type] = {spec.key: spec.value_type for spec in MANIFEST_FIELDS}

# 清单必填项，缺任一拒收
_REQUIRED_KEYS = tuple(spec.key for spec in MANIFEST_FIELDS if spec.required)


def _plugins_dir() -> Path | None:
    """定位插件包目录

    - find_spec 只定位不执行模块代码，冻结包下路径随包走
    - 定位失败返回 None，由调用方处理
    """
    spec = importlib.util.find_spec(PLUGINS_PKG)
    if spec is None or not spec.submodule_search_locations:
        return None
    return Path(next(iter(spec.submodule_search_locations)))


def _load_manifests(plugins_path: Path) -> dict[str, PluginManifestDTO]:
    """扫描插件目录聚合清单

    - 只认含清单文件的直接子目录
    - 按目录名升序插入，dict 保序
    - 读取失败或字段非法的插件跳过
    """
    manifests: dict[str, PluginManifestDTO] = {}

    if not plugins_path.is_dir():
        return manifests

    for path in sorted(plugins_path.iterdir()):
        manifest = _read_manifest(path / PluginFileName.MANIFEST, path.name)
        if manifest is not None:
            manifests[manifest.name] = manifest

    return manifests


def _read_manifest(path: Path, dir_name: str) -> PluginManifestDTO | None:
    """读取单份插件清单文件

    - 文件缺失或解析失败返回 None
    - 必填三项缺失、name 与目录名不符或类型错误则整份拒收
    - 未知键忽略，可选字段缺省用 DTO 默认值
    """
    if not path.is_file():
        return None

    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
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

    if raw_sections := data.get(ManifestKey.HELP):
        kwargs["help_section"] = read_help_sections(raw_sections, dir_name)

    return PluginManifestDTO(**kwargs)


def _load_instance_enabled(state_path: Path) -> frozenset[str] | None:
    """读取实例启用集

    - 只取 enabled 键，随包插件恒启用与回落由 _resolve_enabled 处理
    - 文件不存在或解析失败返回 None，前者即实例从未保存过插件选择
    """
    if not state_path.is_file():
        return None

    try:
        data = tomllib.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return None

    return frozenset(str(name) for name in data.get(StateKey.ENABLED, []))


def _load_catalog(state_path: Path) -> str:
    """读取实例目录指纹

    - 缺失或损坏返回空串，与任何现算指纹都不等
    """
    if not state_path.is_file():
        return ""

    try:
        data = tomllib.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return ""

    return str(data.get(StateKey.CATALOG, ""))


def _resolve_enabled(
    manifests: dict[str, PluginManifestDTO],
    enabled: frozenset[str] | None,
) -> list[PluginManifestDTO]:
    """计算启用插件序列

    - 随包表里的插件恒启用
    - enabled 为 None 表示从未保存过选择，只用随包插件
    - 先按随包表定档，表外插件一律常规档，同档按 name 字典序
    """
    picked = [
        manifest
        for manifest in manifests.values()
        if manifest.name in CORE_PLUGIN_PRIORITY
        or (enabled is not None and manifest.name in enabled)
    ]
    return sorted(
        picked,
        key=lambda m: (
            CORE_PLUGIN_PRIORITY.get(m.name, CommandPriority.NORMAL),
            m.name,
        ),
    )


def enabled_manifests(state_path: Path) -> list[PluginManifestDTO]:
    """读取启用插件的清单序列

    - 注册表与帮助聚合共用本函数取序列
    - 目录定位失败或无清单返回空列表
    """
    found = _plugins_dir()
    if found is None:
        return []
    return _resolve_enabled(_load_manifests(found), _load_instance_enabled(state_path))
