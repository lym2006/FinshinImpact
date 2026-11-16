"""适配器清单读取器

- 目录与已装包两路读声明，同名平台认目录里那份
- 接口包版本要求两路都从依赖声明里取，声明段只自报平台码
- 适配器代码一律从环境里那只包取，装载侧不改搜索路径
- 声明缺失或字段非法的适配器不进表
"""

from dataclasses import dataclass
from importlib.metadata import EntryPoint, entry_points
from pathlib import Path
from typing import Any

from finshin_sdk.domain import (
    ADAPTER_DECLARATION_FILE,
    ADAPTER_ENTRY_ATTR,
    ADAPTER_ENTRY_GROUP,
    ADAPTER_MANIFEST_FIELDS,
    ADAPTERS_PKG,
    AdapterManifestKey,
    Platform,
)
from finshin_sdk.dto import AdapterManifestDTO
from system.distributions import SDK_DISTRIBUTION, requires_of
from system.profile_env import ROOT_DIR
from system.toml_read import read_toml

# 声明里的标量字段与期望类型
_SCALAR_TYPES: dict[AdapterManifestKey, type] = {
    spec.key: spec.value_type
    for spec in ADAPTER_MANIFEST_FIELDS
    if spec.value_type is not list
}

# 声明里的必填字段，缺任一即整份拒收
_REQUIRED_KEYS = tuple(spec.key for spec in ADAPTER_MANIFEST_FIELDS if spec.required)

# 入口点值里模块与属性的分隔符
_ENTRY_SEP = ":"


def load_adapter_manifests() -> dict[Platform, AdapterManifestDTO]:
    """按目录与已装包两路聚合适配器声明

    - 目录先读，同平台的已装包那份不进表
    - 目录按名升序插入并保留顺序
    """
    manifests: dict[Platform, AdapterManifestDTO] = {}
    for dto, _name in _scan_dirs():
        manifests.setdefault(dto.platform, dto)
    for dto in _from_installed():
        manifests.setdefault(dto.platform, dto)

    return manifests


def tree_distributions() -> dict[Platform, str]:
    """挂载仓里在场的那些适配器，交出平台码到声明发行件名的表

    - 同一平台目录里那份优先于已装包，声明从哪来认这个
    """
    return {dto.platform: name for dto, name in _scan_dirs()}


def adapter_deps_union(exclude: Platform | None = None) -> list[str]:
    """汇总各适配器声明的依赖

    - 各适配器全进表，没有启用集能筛
    - 点名排除即只把那一平台的那份摘掉
    """
    return [
        pin
        for dto in load_adapter_manifests().values()
        if exclude is None or dto.platform != exclude
        for pin in dto.deps
    ]


def installed_adapter_pins(exclude: Platform | None = None) -> list[str]:
    """已装适配器包的 pin 清单

    - 目录里的适配器以源码在场，不进这份表
    - 点名排除即只把那一平台的那只摘掉
    """
    # 同步删的是保留清单外的包，缺这一条即连适配器带它的引擎库一起删掉
    pins: list[str] = []
    for point in _installed_points():
        dist = point.dist
        if dist is None or _excluded(point.name, exclude):
            continue
        pins.append(f"{dist.name}=={dist.version}")

    return pins


def _excluded(name: str, exclude: Platform | None) -> bool:
    """入口点名的是不是要点名排除的那一平台

    - 没点名排除即一律不排，平台标识认不出的也留下
    """
    return exclude is not None and _platform_of(name) == exclude


def _adapters_dir() -> Path | None:
    """定位安装目录下的适配器根

    - 根不在盘上返回 None，由调用方处理
    """
    root = ROOT_DIR / ADAPTERS_PKG
    return root if root.is_dir() else None


def _scan_dirs() -> list[tuple[AdapterManifestDTO, str]]:
    """挂载仓里每份认下来的声明，与它声明的发行件名"""
    root = _adapters_dir()
    if root is None:
        return []

    found: list[tuple[AdapterManifestDTO, str]] = []
    for path in sorted(root.iterdir()):
        read = _read_dir(path)
        if read is not None:
            found.append(read)

    return found


def _read_dir(adapter_dir: Path) -> tuple[AdapterManifestDTO, str] | None:
    """读取适配器声明

    - 文件缺失或解析失败返回 None
    - 必填项缺失、字段空值、平台标识非法则整份拒收
    - 数组字段缺省为空表，出现非字符串或空串项同样整份拒收
    - 入口点没点名本平台、或属性名不合本体规定，整份拒收
    - 认下来交出声明与项目名，代码仍取环境里那只包
    """
    data = read_toml(adapter_dir / ADAPTER_DECLARATION_FILE)
    if data is None:
        return None

    values = _declared_values(data)
    if values is None:
        return None

    platform = _platform_of(values[AdapterManifestKey.PLATFORM])
    if platform is None:
        return None

    entry = _entry_module(data, platform)
    if entry is None:
        return None

    deps = values[AdapterManifestKey.DEPS]

    return (
        AdapterManifestDTO(
            platform=platform,
            deps=deps,
            requires_sdk=requires_of(deps, SDK_DISTRIBUTION),
            entry=entry,
        ),
        _project_name(data),
    )


def _project_name(data: dict[str, Any]) -> str:
    """声明里的项目名，缺键或非串交出空串"""
    value = _dig(data, "project.name")
    return value if isinstance(value, str) else ""


def _declared_values(data: dict[str, Any]) -> dict[str, Any] | None:
    """按字段表读取声明值"""
    values: dict[str, Any] = {}
    for spec in ADAPTER_MANIFEST_FIELDS:
        raw = _dig(data, spec.key.value)
        if spec.value_type is list:
            if raw is None:
                values[spec.key] = ()
                continue
            if not isinstance(raw, list) or not all(
                isinstance(item, str) and item for item in raw
            ):
                return None
            values[spec.key] = tuple(raw)
            continue

        if raw is None:
            if spec.key in _REQUIRED_KEYS:
                return None
            continue
        if not isinstance(raw, _SCALAR_TYPES[spec.key]) or not raw:
            return None
        values[spec.key] = raw

    return values


def _dig(data: dict[str, Any], key: str) -> Any:
    """按分层键名取值"""
    node: Any = data
    for part in key.split("."):
        if not isinstance(node, dict):
            return None
        node = node.get(part)

    return node


def _entry_module(data: dict[str, Any], platform: Platform) -> str | None:
    """读取本平台入口模块名

    - 段名即本体规定的入口点组，键为平台标识
    - 值写作「模块:属性」，属性名不合本体规定的整份不算
    """
    project = data.get("project")
    points = (project or {}).get("entry-points") if isinstance(project, dict) else None
    table = points.get(ADAPTER_ENTRY_GROUP) if isinstance(points, dict) else None
    if not isinstance(table, dict):
        return None

    value = table.get(str(platform))
    if not isinstance(value, str):
        return None

    module, sep, attr = value.partition(_ENTRY_SEP)
    if not sep or not module or attr != ADAPTER_ENTRY_ATTR:
        return None

    return module


def _from_installed() -> list[AdapterManifestDTO]:
    """聚合已装适配器声明

    - 平台标识取入口点的名，入口模块取值的冒号前段
    - 依赖取包元数据声明的顶层依赖
    - 接口包版本要求也从这串依赖里取
    """
    return [
        AdapterManifestDTO(
            platform=item.platform,
            deps=item.requires,
            requires_sdk=requires_of(item.requires, SDK_DISTRIBUTION),
            entry=item.entry,
        )
        for item in installed_adapters()
    ]


@dataclass(frozen=True, slots=True)
class InstalledAdapter:
    """一只已装的适配器包

    - 平台码取入口点名，发行件名与版本取包元数据
    """

    platform: Platform
    distribution: str
    version: str
    requires: tuple[str, ...]
    entry: str


def installed_adapters() -> tuple[InstalledAdapter, ...]:
    """列已装且本体认得平台的适配器包

    - 平台码不在词表、或入口属性名不合本体规定的不进表
    """
    found: list[InstalledAdapter] = []
    for point in _installed_points():
        platform = _platform_of(point.name)
        dist = point.dist
        if platform is None or dist is None or point.attr != ADAPTER_ENTRY_ATTR:
            continue
        found.append(
            InstalledAdapter(
                platform=platform,
                distribution=str(dist.name),
                version=str(dist.version),
                requires=tuple(str(pin) for pin in dist.requires or []),
                entry=point.module,
            )
        )

    return tuple(found)


def _installed_points() -> tuple[EntryPoint, ...]:
    """取本体规定的入口点组里在场的那些"""
    return tuple(entry_points(group=ADAPTER_ENTRY_GROUP))


def _platform_of(name: str) -> Platform | None:
    """认平台标识"""
    try:
        return Platform(name)
    except ValueError:
        return None
