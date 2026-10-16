# src/bootstrap/_plugin/_manifest.py
"""引导期插件清单

- 面板与启动判定读清单、算指纹、读写实例状态
- 引导期不得 import utils
"""

import hashlib
import importlib.util
import re
import tomllib
from pathlib import Path
from typing import Any

from core.domain import (
    MANIFEST_FIELDS,
    PLUGINS_PKG,
    ManifestKey,
    PluginFile,
    StateKey,
)
from profile_env import INSTANCES_DIR, ROOT_DIR, profile_dir

# 依赖 pin 串顶层包名截断符，"playwright>=1.40" 切出 "playwright"
_PIN_SPLIT = re.compile(r"[<>=!~\[;\s]+")

# 面板与裁决所需的最小字段集，help 段面板不消费故排除
_MINIMAL_KEYS = frozenset(spec.key for spec in MANIFEST_FIELDS)

_DEFAULTS: dict[str, Any] = {spec.key: spec.default for spec in MANIFEST_FIELDS}


def plugins_root() -> Path | None:
    """定位插件包目录

    - find_spec 只定位不执行模块代码
    """
    spec = importlib.util.find_spec(PLUGINS_PKG)
    if spec is None or not spec.submodule_search_locations:
        return None
    return Path(next(iter(spec.submodule_search_locations)))


def _read_toml(path: Path) -> dict[str, Any] | None:
    """读取 TOML 文件

    - 缺失或解析失败返回 None
    """
    if not path.is_file():
        return None
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return None


def load_manifests(plugins_path: Path) -> list[dict[str, Any]]:
    """扫描插件目录聚合最小清单

    - 无清单或 name 非法的子目录跳过
    - 按 (order, name) 升序返回 dict 列表
    """
    manifests: list[dict[str, Any]] = []

    if not plugins_path.is_dir():
        return manifests

    for path in sorted(plugins_path.iterdir()):
        data = _read_toml(path / PluginFile.MANIFEST)
        if not data or not isinstance(data.get(ManifestKey.NAME), str):
            continue
        manifests.append({key: data.get(key, _DEFAULTS[key]) for key in _MINIMAL_KEYS})

    manifests.sort(key=lambda item: (item[ManifestKey.ORDER], item[ManifestKey.NAME]))
    return manifests


def catalog_digest(manifests: list[dict[str, Any]]) -> str:
    """计算目录指纹

    - 只摘要 name+deps+assets，展示文案变化不触发弹面板
    - 行序与扫描顺序无关，同集合必同摘要
    """
    items = sorted(
        f"{m[ManifestKey.NAME]}"
        f"|{'|'.join(m[ManifestKey.DEPS])}"
        f"|{'|'.join(m[ManifestKey.ASSETS])}"
        for m in manifests
    )
    return hashlib.sha256("\n".join(items).encode("utf-8")).hexdigest()


def _state_path_of(code: str) -> Path:
    """按身份码定位实例状态文件"""
    return profile_dir(code) / PluginFile.STATE


def load_state(code: str) -> dict[str, Any]:
    """读取实例插件状态

    - 文件不存在或解析失败返回空字典，前者即实例从未保存过插件选择
    """
    return _read_toml(_state_path_of(code)) or {}


def panel_needed(code: str) -> bool:
    """判断是否需要自动弹面板

    - 状态缺失、缺 catalog 字段或指纹与现目录不符，任一为真
    - 用户取消面板则放弃本次启动，调用方按 CANCEL 处理
    """
    state = load_state(code)
    catalog = state.get(StateKey.CATALOG)
    if not isinstance(catalog, str) or not catalog:
        return True
    root = plugins_root()
    if root is None:
        return False
    return catalog_digest(load_manifests(root)) != catalog


def save_state(code: str, enabled: list[str], catalog: str) -> None:
    """写实例插件状态

    - core 插件不写进 enabled，读取侧恒并入
    - 引导期写入用 tomlkit，运行期只读不写
    """
    import tomlkit

    doc = tomlkit.document()
    doc.add(StateKey.ENABLED, enabled)
    doc.add(StateKey.CATALOG, catalog)
    target = _state_path_of(code)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(tomlkit.dumps(doc), encoding="utf-8")


def top_package_name(pin: str) -> str:
    """从依赖 pin 串截出顶层包名"""
    return _PIN_SPLIT.split(pin, 1)[0]


def core_dependencies() -> list[str]:
    """读取项目核心依赖清单

    - 取 pyproject 的 project.dependencies 段
    - 发布包内 pyproject 为随包文件，缺失返回空表由调用方处理
    """
    data = _read_toml(ROOT_DIR / "pyproject.toml") or {}
    return list(data.get("project", {}).get("dependencies", []))


def dev_dependencies() -> list[str]:
    """读取 dev 可选依赖清单

    - 来源 pyproject 的 project.optional-dependencies.dev
    - 仅供同步环境时保留已装工具，缺段返回空表
    """
    data = _read_toml(ROOT_DIR / "pyproject.toml") or {}
    optional = data.get("project", {}).get("optional-dependencies", {})
    return list(optional.get("dev", []))


def enabled_deps_union(exclude_code: str = "") -> list[str]:
    """汇总全部实例已启用插件的依赖并集

    - exclude_code 为本次操作发起实例，卸载判定须排除
    """
    return _enabled_field_union(exclude_code, ManifestKey.DEPS)


def _enabled_field_union(exclude_code: str, field: str) -> list[str]:
    """按清单字段汇总其他实例的启用并集

    - 实例目录逐个子目录扫状态文件，目录不存在返回空表
    """
    items: list[str] = []
    if not INSTANCES_DIR.is_dir():
        return items

    root = plugins_root()
    manifests = load_manifests(root) if root else []
    for path in sorted(INSTANCES_DIR.iterdir()):
        if not path.is_dir() or path.name == exclude_code:
            continue
        enabled = set(load_state(path.name).get(StateKey.ENABLED, []))
        if not enabled:
            continue
        for manifest in manifests:
            if manifest[ManifestKey.NAME] in enabled:
                items.extend(manifest[field])
    return items
