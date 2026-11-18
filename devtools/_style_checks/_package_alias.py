"""被扫文件的点分模块名怎么算

- 有改名声明的按声明算：以各仓项目声明里的 setuptools 改名表为准，不靠目录名猜
- 没有声明才沿 `__init__.py` 链上溯
- 声明从被扫文件所在目录逐级上溯到扫描根，取第一份罩得住它的
- 同一份声明在一次扫描内按所在目录缓存，只解析一遍
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

# 声明载体文件名，与改名表在声明里的位置
_DECLARATION_NAME = "pyproject.toml"
_PACKAGE_DIR_PATH: tuple[str, ...] = ("tool", "setuptools", "package-dir")

# 缓存键是声明所在目录，值是展开成绝对路径的「源码目录 → 包名」
AliasCache = dict[Path, dict[Path, str]]


def module_name(path: Path, root: Path, cache: AliasCache) -> str:
    """算出被扫文件的点分模块名"""
    alias = _lookup_alias(path, root, cache)
    if alias is not None:
        return _aliased(path, alias)
    if path.name == "__init__.py":
        parts: list[str] = []
        cur = path.parent
    else:
        parts = [path.stem]
        cur = path.parent
    while (cur / "__init__.py").is_file() and cur != root:
        parts.append(cur.name)
        cur = cur.parent
    return ".".join(reversed(parts))


def _aliased(path: Path, alias: tuple[str, Path]) -> str:
    """把声明里的源码目录换成包名前缀，目录自身的门面文件退回目录名"""
    name, source_dir = alias
    parts = list(path.relative_to(source_dir).parts)
    parts[-1] = parts[-1].removesuffix(".py")
    if parts[-1] == "__init__":
        parts.pop()
    if name:
        return ".".join([name, *parts])
    return ".".join(parts) if parts else source_dir.name


def _lookup_alias(path: Path, root: Path, cache: AliasCache) -> tuple[str, Path] | None:
    """交出罩住这个文件的「包名与它的源码目录」，没有声明返回 None"""
    for base in _upwards(path.parent, root):
        for source_dir, name in _table(base, cache).items():
            if source_dir in path.parents:
                return name, source_dir
    return None


def _upwards(start: Path, root: Path) -> Iterator[Path]:
    """从 start 逐级上溯到 root，两端都含"""
    current = start
    while True:
        yield current
        if current == root or current.parent == current:
            return
        current = current.parent


def _table(base: Path, cache: AliasCache) -> dict[Path, str]:
    """取 base 下的改名表，键换成绝对源码目录"""
    if base not in cache:
        cache[base] = _read_table(base)
    return cache[base]


def _read_table(base: Path) -> dict[Path, str]:
    """解析 base 那份声明的改名表，没有该段即交空表"""
    declared = _dig(_load(base / _DECLARATION_NAME))
    if not isinstance(declared, dict):
        return {}
    return {
        (base / str(source_dir)).resolve(): str(name)
        for name, source_dir in declared.items()
    }


def _load(declaration: Path) -> object:
    """读声明原文，文件不存在交空字典"""
    if not declaration.is_file():
        return {}
    with declaration.open("rb") as handle:
        return tomllib.load(handle)


def _dig(data: object) -> object:
    """按位置逐级取值，任一级不是表即交空字典"""
    current = data
    for key in _PACKAGE_DIR_PATH:
        if not isinstance(current, dict):
            return {}
        current = current.get(key)
    return current
