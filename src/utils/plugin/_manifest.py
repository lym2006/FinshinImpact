# src/utils/plugin/_manifest.py
"""插件清单读取器

- 扫描插件目录聚合各插件自描述清单
- 读取实例状态文件并计算启用序列
- 引导期另有一份精简实现，见 services/env_setup/deps_manifest.py 互注
"""

import importlib.util
import tomllib
from pathlib import Path
from typing import Any, TypeGuard

from core.domain import (
    MANIFEST_FIELDS,
    ORDER_TIERS,
    PLUGINS_PKG,
    CommandPriority,
    HelpKey,
    ManifestKey,
    PluginFileName,
    StateKey,
)
from core.dto import HelpCommandDTO, HelpSectionDTO, PluginManifestDTO

# 清单标量字段与期望类型，deps/assets 列表成员一律 str
_SCALAR_TYPES: dict[str, type] = {spec.key: spec.value_type for spec in MANIFEST_FIELDS}

# 帮助贡献键名白名单，未知键段整段拒收
_HELP_SECTION_KEYS = frozenset({HelpKey.SECTION, HelpKey.NOTE, HelpKey.COMMANDS})
_HELP_COMMAND_KEYS = frozenset({HelpKey.CMD, HelpKey.DESC})
_HELP_COMMAND_ALLOWED = _HELP_COMMAND_KEYS | frozenset({HelpKey.FLAGS})

# 清单开关项的段数：开关与说明各一段
_FLAG_ITEM_LEN = 2

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

    if (raw_order := data.get(ManifestKey.ORDER)) is not None:
        if not isinstance(raw_order, int) or raw_order not in ORDER_TIERS:
            return None
        kwargs[ManifestKey.ORDER] = CommandPriority(raw_order)

    if raw_sections := data.get(ManifestKey.HELP):
        kwargs["help_section"] = _read_help_sections(raw_sections)

    return PluginManifestDTO(**kwargs)


def _read_help_sections(
    raw_sections: object,
) -> tuple[HelpSectionDTO, ...]:
    """解析帮助贡献段列表

    - 非列表入参视为无贡献
    - 段含未知键或类型错误时整段跳过
    - 单条命令键集或类型不符时该条跳过
    """
    if not isinstance(raw_sections, list):
        return ()

    sections: list[HelpSectionDTO] = []
    for raw_section in raw_sections:
        if not isinstance(raw_section, dict):
            continue
        if not _HELP_SECTION_KEYS.issuperset(raw_section):
            continue

        section = raw_section.get(HelpKey.SECTION, "")
        note = raw_section.get(HelpKey.NOTE, "")
        raw_commands = raw_section.get(HelpKey.COMMANDS, [])
        if not isinstance(section, str) or not isinstance(note, str):
            continue
        if not isinstance(raw_commands, list):
            continue

        commands = tuple(
            command
            for command in map(_parse_help_command, raw_commands)
            if command is not None
        )
        sections.append(HelpSectionDTO(section=section, note=note, commands=commands))

    return tuple(sections)


def _parse_help_command(raw: object) -> HelpCommandDTO | None:
    """解析单条命令贡献

    - 键集超出清单口径或必填类型不符时返回 None
    - flags 可缺省，缺省为空元组
    - 每项须是「开关 说明」两段非空文本
    """
    if not isinstance(raw, dict):
        return None
    if not _HELP_COMMAND_KEYS.issubset(raw) or not _HELP_COMMAND_ALLOWED.issuperset(
        raw
    ):
        return None
    if not all(isinstance(raw[key], str) for key in _HELP_COMMAND_KEYS):
        return None

    raw_flags = raw.get(HelpKey.FLAGS, [])
    if not isinstance(raw_flags, list):
        return None
    flags: list[tuple[str, str]] = []
    for raw_flag in raw_flags:
        if not _is_flag_item(raw_flag):
            return None
        flags.append((raw_flag[0], raw_flag[1]))

    return HelpCommandDTO(
        cmd=raw[HelpKey.CMD],
        desc=raw[HelpKey.DESC],
        flags=tuple(flags),
    )


def _is_flag_item(raw_flag: object) -> TypeGuard[list[str]]:
    """判定开关项是否为两段非空文本

    - 段数、类型或空串任一不符即判否
    """
    return (
        isinstance(raw_flag, list)
        and len(raw_flag) == _FLAG_ITEM_LEN
        and all(isinstance(part, str) and part for part in raw_flag)
    )


def _load_instance_enabled(state_path: Path) -> frozenset[str] | None:
    """读取实例启用集

    - 只取 enabled 键，core 并入与回落由 _resolve_enabled 处理
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

    - core 恒启用
    - enabled 为 None 表示从未保存过选择，只用 core
    - 按 (order, name) 升序，同值按 name 字典序
    """
    picked = [
        manifest
        for manifest in manifests.values()
        if manifest.core or (enabled is not None and manifest.name in enabled)
    ]
    return sorted(picked, key=lambda m: (m.order, m.name))


def enabled_manifests(state_path: Path) -> list[PluginManifestDTO]:
    """读取启用插件的清单序列

    - 注册表与帮助聚合共用本函数取序列
    - 目录定位失败或无清单返回空列表
    """
    found = _plugins_dir()
    if found is None:
        return []
    return _resolve_enabled(_load_manifests(found), _load_instance_enabled(state_path))
