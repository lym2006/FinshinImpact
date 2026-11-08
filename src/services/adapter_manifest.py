# src/services/adapter_manifest.py
"""适配器清单读取器

- 扫描适配器目录聚合各适配器自描述清单
- 清单缺失或字段非法的适配器不进表
"""

import importlib.util
import tomllib
from pathlib import Path
from typing import Any

from core.domain import (
    ADAPTER_ENTRY_MODULE,
    ADAPTER_MANIFEST_FIELDS,
    ADAPTER_MANIFEST_FILE,
    ADAPTERS_PKG,
    AdapterManifestKey,
    Platform,
)
from core.dto import AdapterManifestDTO

# 清单标量字段与期望类型
_SCALAR_TYPES: dict[str, type] = {
    spec.key: spec.value_type for spec in ADAPTER_MANIFEST_FIELDS
}

# 清单必填项，缺任一拒收
_REQUIRED_KEYS = tuple(spec.key for spec in ADAPTER_MANIFEST_FIELDS if spec.required)


def _adapters_dir() -> Path | None:
    """定位适配器包目录

    - find_spec 只定位不执行模块代码，冻结包下路径随包走
    - 定位失败返回 None，由调用方处理
    """
    spec = importlib.util.find_spec(ADAPTERS_PKG)
    if spec is None or not spec.submodule_search_locations:
        return None
    return Path(next(iter(spec.submodule_search_locations)))


def load_adapter_manifests() -> dict[Platform, AdapterManifestDTO]:
    """扫描适配器目录聚合清单

    - 只认含清单文件的直接子目录
    - 按目录名升序插入，dict 保序
    - 同一平台有多份清单时只留先读到的
    """
    manifests: dict[Platform, AdapterManifestDTO] = {}

    adapters_path = _adapters_dir()
    if adapters_path is None or not adapters_path.is_dir():
        return manifests

    for path in sorted(adapters_path.iterdir()):
        manifest = _read_manifest(path / ADAPTER_MANIFEST_FILE, path.name)
        if manifest is not None and manifest.platform not in manifests:
            manifests[manifest.platform] = manifest

    return manifests


def _read_manifest(path: Path, dir_name: str) -> AdapterManifestDTO | None:
    """读取单份适配器清单文件

    - 文件缺失或解析失败返回 None
    - 必填项缺失、字段空值、平台标识非法则整份拒收
    - 未知键忽略，入口模块按本体规定的名字定位
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
        if not isinstance(value, expected) or not value:
            return None
        kwargs[key] = value

    if not all(k in kwargs for k in _REQUIRED_KEYS):
        return None

    try:
        platform = Platform(kwargs[AdapterManifestKey.PLATFORM])
    except ValueError:
        return None

    return AdapterManifestDTO(
        platform=platform,
        version=kwargs[AdapterManifestKey.VERSION],
        entry=f"{ADAPTERS_PKG}.{dir_name}.{ADAPTER_ENTRY_MODULE}",
    )
