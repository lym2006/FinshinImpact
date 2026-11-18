"""非 py 载体名单

- 定义随装载入口一并读取的发布记录根、入库 md 载体根与排除目录
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

# md 载体根名单，README.md 按文件取，另两项整树递归
_MD_FILE_ROOTS: tuple[str, ...] = ("README.md",)
_MD_DIR_ROOTS: tuple[str, ...] = ("docs", "assets")

# docs 下工作底稿不进判定范围，按目录段整树排除
_MD_SKIP_DIRS: frozenset[str] = frozenset({"design"})


def iter_md(root: Path, changelog_name: str) -> Iterator[Path]:
    """枚举恒随装载入口读取的发布记录与入库 md"""
    changelog = root / changelog_name
    if changelog.is_file():
        yield changelog
    for name in _MD_FILE_ROOTS:
        path = root / name
        if path.is_file():
            yield path
    for name in _MD_DIR_ROOTS:
        base = root / name
        if not base.is_dir():
            continue
        for path in base.rglob("*.md"):
            if _MD_SKIP_DIRS.isdisjoint(path.relative_to(base).parts):
                yield path
