# src/services/env_setup/deps_manifest.py
"""插件依赖清单

- 面板与启动判定读清单、算指纹、读写实例状态
"""

import hashlib
import importlib.util
import re
import tomllib
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from core.domain import (
    BUNDLED_PLUGIN_PRIORITY,
    INSTALLED_PLUGINS_NAME,
    MANIFEST_FIELDS,
    PLUGINS_PKG,
    CommandPriority,
    HelpKey,
    ManifestKey,
    PluginFileName,
    StateKey,
)
from system.profile_env import INSTANCES_DIR, ROOT_DIR, profile_dir

# 依赖 pin 串顶层包名截断符，"playwright>=1.40" 切出 "playwright"
_PIN_SPLIT = re.compile(r"[<>=!~\[;\s]+")

# 面板与裁决所需的最小字段集，help 段只取命令名
_MINIMAL_KEYS = frozenset(spec.key for spec in MANIFEST_FIELDS)

_DEFAULTS: dict[str, Any] = {spec.key: spec.default for spec in MANIFEST_FIELDS}

# 单条命令的必填两键，缺任一的条目不算命令名
_COMMAND_KEYS = frozenset({HelpKey.CMD, HelpKey.DESC})


def plugins_roots() -> list[Path]:
    """列出插件根目录，随包在前外部在后

    - find_spec 只定位不执行模块代码
    - 外部目录不存在即不进表
    """
    roots: list[Path] = []

    spec = importlib.util.find_spec(PLUGINS_PKG)
    if spec is not None and spec.submodule_search_locations:
        roots.append(Path(next(iter(spec.submodule_search_locations))))

    installed = ROOT_DIR / INSTALLED_PLUGINS_NAME
    if installed.is_dir():
        roots.append(installed)

    return roots


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


def _scan_rows(plugins_paths: Sequence[Path]) -> list[dict[str, Any]]:
    """按根的顺序逐子目录读出最小清单，同名不去重

    - 无清单或 name 非法的子目录跳过
    - 每行带 help 段声明的命令名，供命令名抢占判定取用
    """
    rows: list[dict[str, Any]] = []
    for plugins_path in plugins_paths:
        if not plugins_path.is_dir():
            continue

        for path in sorted(plugins_path.iterdir()):
            data = _read_toml(path / PluginFileName.MANIFEST)
            if not data or not isinstance(data.get(ManifestKey.NAME), str):
                continue
            row: dict[str, Any] = {
                key: data.get(key, _DEFAULTS[key]) for key in _MINIMAL_KEYS
            }
            row[HelpKey.COMMANDS] = _command_names(data)
            rows.append(row)

    return rows


def load_manifests(plugins_paths: Sequence[Path]) -> list[dict[str, Any]]:
    """扫描插件根目录聚合最小清单

    - 同名插件按根的顺序取先读到的，随包压住外部同名
    - 随包表里的先成一组，组内按档位序，其余一律排在后并按 name 字典序
    """
    found: dict[str, dict[str, Any]] = {}
    for row in _scan_rows(plugins_paths):
        found.setdefault(row[ManifestKey.NAME], row)

    return sorted(
        found.values(),
        key=lambda item: (
            item[ManifestKey.NAME] not in BUNDLED_PLUGIN_PRIORITY,
            BUNDLED_PLUGIN_PRIORITY.get(item[ManifestKey.NAME], CommandPriority.NORMAL),
            item[ManifestKey.NAME],
        ),
    )


def shadowed_manifests(
    plugins_paths: Sequence[Path],
) -> list[tuple[dict[str, Any], str]]:
    """读出被同名前一份顶掉的插件行

    - 回 (被顶掉的清单, 顶掉它的那份的名字) 序列
    - 名字先被哪一根目录读到，后一根目录里的同名那份即整只不装载
    - 面板据此给被顶掉的那一份补一行冲突明细
    """
    claimed: set[str] = set()
    shadowed: list[tuple[dict[str, Any], str]] = []
    for row in _scan_rows(plugins_paths):
        name = row[ManifestKey.NAME]
        if name in claimed:
            shadowed.append((row, name))
            continue
        claimed.add(name)

    return shadowed


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


def _command_names(data: dict[str, Any]) -> tuple[str, ...]:
    """从清单 help 段取命令名

    - 段与条目的形状不符即跳过该项
    - 必填两键齐了才算一条命令名
    """
    sections = data.get(ManifestKey.HELP)
    if not isinstance(sections, list):
        return ()

    names: list[str] = []
    for section in sections:
        if not isinstance(section, dict):
            continue
        for command in section.get(HelpKey.COMMANDS, []):
            if not isinstance(command, dict):
                continue
            if all(isinstance(command.get(key), str) for key in _COMMAND_KEYS):
                names.append(command[HelpKey.CMD])

    return tuple(names)


def _state_path_of(code: str) -> Path:
    """按身份码定位实例状态文件"""
    return profile_dir(code) / PluginFileName.STATE


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
    roots = plugins_roots()
    if not roots:
        return False
    return catalog_digest(load_manifests(roots)) != catalog


def save_state(code: str, enabled: list[str], catalog: str) -> None:
    """写实例插件状态

    - 随包插件不写进 enabled，读取侧恒并入
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


def _core_dependencies() -> list[str]:
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


def _enabled_deps_union(exclude_code: str = "") -> list[str]:
    """汇总全部实例已启用插件的依赖并集

    - exclude_code 为本次操作发起实例，卸载判定须排除
    """
    return _enabled_field_union(exclude_code, ManifestKey.DEPS)


def keep_union() -> list[str]:
    """全局保留清单

    - 核心依赖与全实例启用插件依赖并集
    - 本实例刚保存的启用集已在盘上，并集即最新状态
    """
    return [*_core_dependencies(), *_enabled_deps_union()]


def _enabled_field_union(exclude_code: str, field: str) -> list[str]:
    """按清单字段汇总其他实例的启用并集

    - 实例目录逐个子目录扫状态文件，目录不存在返回空表
    """
    items: list[str] = []
    if not INSTANCES_DIR.is_dir():
        return items

    manifests = load_manifests(plugins_roots())
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
