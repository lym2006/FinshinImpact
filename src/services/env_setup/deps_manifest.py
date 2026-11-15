"""插件依赖清单

- 面板与启动判定读清单、算指纹、读写实例状态
- 外部插件的库取自家声明的依赖表，随包插件的库在根声明里
"""

import importlib.util
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from finshin_sdk.domain import (
    BUNDLED_PLUGIN_PRIORITY,
    INSTALLED_PLUGINS_NAME,
    INSTALLED_PLUGINS_PKG,
    MANIFEST_FIELDS,
    PLUGINS_PKG,
    HelpKey,
    ManifestKey,
    PluginFileName,
    StateKey,
)
from system.atomic_write import write_text_atomic
from system.digest import lines_digest
from system.profile_env import DECLARATION_FILE_NAME, ROOT_DIR, profile_dir
from system.toml_read import read_toml
from system.tool_settings import declared_dependencies

# 依赖 pin 串顶层包名截断符，"playwright>=1.40" 切出 "playwright"
_PIN_SPLIT = re.compile(r"[<>=!~\[;\s]+")

# 面板与裁决所需的最小字段集，help 段只取命令名
_MINIMAL_KEYS = frozenset(spec.key for spec in MANIFEST_FIELDS)

_DEFAULTS: dict[str, Any] = {spec.key: spec.default for spec in MANIFEST_FIELDS}

# 插件根：目录与这棵树的顶层包名
_PluginRoot = tuple[Path, str]

# 单条命令的必填两键，缺任一的条目不算命令名
_COMMAND_KEYS = frozenset({HelpKey.CMD, HelpKey.DESC})


def plugins_roots() -> list[_PluginRoot]:
    """列出插件根与各自的顶层包名，随包在前外部在后

    - 外部目录不存在即不进表
    """
    roots: list[_PluginRoot] = []

    spec = importlib.util.find_spec(PLUGINS_PKG)
    if spec is not None and spec.submodule_search_locations:
        roots.append((Path(next(iter(spec.submodule_search_locations))), PLUGINS_PKG))

    installed = ROOT_DIR / INSTALLED_PLUGINS_NAME
    if installed.is_dir():
        roots.append((installed, INSTALLED_PLUGINS_PKG))

    return roots


def _scan_rows(roots: Sequence[_PluginRoot]) -> list[dict[str, Any]]:
    """按目录顺序读取最小清单

    - 无清单或名称非法的子目录跳过
    - 外部那份的自家依赖表读不出即整份不认
    - 每行带帮助段声明的命令名与说明，命令名供抢占判定取用
    """
    rows: list[dict[str, Any]] = []
    for plugins_path, pkg in roots:
        if not plugins_path.is_dir():
            continue

        for path in sorted(plugins_path.iterdir()):
            data = read_toml(path / PluginFileName.MANIFEST)
            if not data or not isinstance(data.get(ManifestKey.NAME), str):
                continue
            deps = _deps_of(path, pkg)
            if deps is None:
                continue
            row: dict[str, Any] = {ManifestKey.DEPS: deps}
            for key in _MINIMAL_KEYS:
                row[key] = data.get(key, _DEFAULTS[key])
            row[HelpKey.COMMANDS] = _command_pairs(data)
            rows.append(row)

    return rows


def _deps_of(plugin_dir: Path, pkg: str) -> tuple[str, ...] | None:
    """一只插件的库，随包那份按根声明算即空表

    - 外部那份交出 None 即自家声明的依赖表读不出，整份不认
    """
    if pkg == PLUGINS_PKG:
        return ()

    return declared_dependencies(plugin_dir / DECLARATION_FILE_NAME)


def load_manifests(roots: Sequence[_PluginRoot]) -> list[dict[str, Any]]:
    """扫描插件根目录聚合最小清单

    - 同名插件按根的顺序取先读到的，随包压住外部同名
    - 随包表里的先成一组，两组组内都按显示名的拼音序
    """
    found: dict[str, dict[str, Any]] = {}
    for row in _scan_rows(roots):
        found.setdefault(row[ManifestKey.NAME], row)

    return sorted(found.values(), key=_sort_key)


def shadowed_manifests(
    roots: Sequence[_PluginRoot],
) -> list[tuple[dict[str, Any], str]]:
    """读出被同名前一份顶掉的插件行

    - 回 (被顶掉的清单, 顶掉它的那份的名字) 序列
    - 名字先被哪一根目录读到，后一根目录里的同名那份即整只不装载
    - 面板据此给被顶掉的那一份补一行冲突明细
    """
    claimed: set[str] = set()
    shadowed: list[tuple[dict[str, Any], str]] = []
    for row in _scan_rows(roots):
        name = row[ManifestKey.NAME]
        if name in claimed:
            shadowed.append((row, name))
            continue
        claimed.add(name)

    return shadowed


def catalog_digest(manifests: list[dict[str, Any]]) -> str:
    """计算目录指纹

    - 只摘要名称、依赖与资源，展示文案变化不触发弹面板
    - 行序与扫描顺序无关，同集合必同摘要
    """
    items = sorted(
        f"{m[ManifestKey.NAME]}"
        f"|{'|'.join(m[ManifestKey.DEPS])}"
        f"|{'|'.join(m[ManifestKey.ASSETS])}"
        for m in manifests
    )
    return lines_digest(items)


def _sort_key(row: dict[str, Any]) -> tuple[Any, ...]:
    """拼面板行序的排序键

    - 先分来源组，组内按显示名的拼音序
    - 显示名取标题列，没填标题时退化成目录名
    - 同拼音按显示名整串，再同按目录名
    """
    display = row[ManifestKey.TITLE] or row[ManifestKey.NAME]
    return (
        row[ManifestKey.NAME] not in BUNDLED_PLUGIN_PRIORITY,
        _pinyin_key(display),
        display.lower(),
        row[ManifestKey.NAME],
    )


def _pinyin_key(text: str) -> tuple[str, ...]:
    """把文本切成拼音片段用于排序

    - 非汉字片段原样保留，中英混排的标题照该片段比
    """
    from pypinyin import lazy_pinyin

    return tuple(piece.lower() for piece in lazy_pinyin(text))


def _command_pairs(data: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    """读取命令名与说明

    - 段与条目的形状不符即跳过该项
    - 必填两键齐了才算一条
    """
    sections = data.get(ManifestKey.HELP)
    if not isinstance(sections, list):
        return ()

    commands: list[tuple[str, str]] = []
    for section in sections:
        if not isinstance(section, dict):
            continue
        for command in section.get(HelpKey.COMMANDS, []):
            if not isinstance(command, dict):
                continue
            if all(isinstance(command.get(key), str) for key in _COMMAND_KEYS):
                commands.append((command[HelpKey.CMD], command[HelpKey.DESC]))

    return tuple(commands)


def _state_path_of(code: str) -> Path:
    """按身份码定位实例状态文件"""
    return profile_dir(code) / PluginFileName.STATE


def load_state(code: str) -> dict[str, Any]:
    """读取实例插件状态

    - 文件不存在或解析失败返回空字典，前者即实例从未保存过插件选择
    """
    return read_toml(_state_path_of(code)) or {}


def panel_needed(code: str) -> bool:
    """判断是否需要自动弹面板

    - 状态缺失、缺目录指纹或指纹与现目录不符，任一为真
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

    - 随包插件不写进启用集，读取侧恒并入
    - 引导期写入，运行期只读不写
    """
    import tomlkit

    doc = tomlkit.document()
    doc.add(StateKey.ENABLED, enabled)
    doc.add(StateKey.CATALOG, catalog)
    target = _state_path_of(code)
    target.parent.mkdir(parents=True, exist_ok=True)
    write_text_atomic(target, tomlkit.dumps(doc))


def top_package_name(pin: str) -> str:
    """从依赖 pin 串截出顶层包名"""
    return _PIN_SPLIT.split(pin, 1)[0]
