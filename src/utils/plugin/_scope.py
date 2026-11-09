# src/utils/plugin/_scope.py
"""外部插件的引用范围检查

- 只查来路在外的件，随包件与本体同一个版本、动一起动
- 导入之前先扫一遍源码，本体各层一律不许引
"""

import ast
import importlib.util
from pathlib import Path

from exceptions import PluginImportError
from finshin_sdk.domain import PLUGINS_PKG
from finshin_sdk.dto import PluginManifestDTO

# 外部插件不许引的本体顶层包，接口包与标准库不在其中
_BODY_ROOTS = frozenset(
    {
        "adapters",
        "bootstrap",
        "bot",
        "bundled",
        "core",
        "data",
        "exceptions",
        "services",
        "skin",
        "system",
        "ui",
        "utils",
    }
)


def check_external_scope(manifest: PluginManifestDTO) -> None:
    """扫外部插件的源码，引了本体内部即拒装

    - 随包树里的件不查：它们与本体同一个版本，动一起动
    - 按清单的导入路径定位目录，只定位不执行
    - 目录定位不到即放过，缺件那步自有另一句报
    """
    if manifest.module.partition(".")[0] == PLUGINS_PKG:
        return
    for file in _source_files(manifest.module):
        offence = _first_body_import(file)
        if offence is not None:
            raise PluginImportError(manifest.name, offence[0], offence[1])


def _source_files(module: str) -> list[Path]:
    """列出这只插件目录里的源码文件"""
    spec = importlib.util.find_spec(module)
    if spec is None:
        return []
    dirs = list(spec.submodule_search_locations or [])
    if not dirs and spec.origin:
        dirs = [str(Path(spec.origin).parent)]
    return sorted(path for root in dirs for path in Path(root).rglob("*.py"))


def _first_body_import(file: Path) -> tuple[str, str] | None:
    """取这份文件里第一处伸向本体的导入

    - 交出「引了谁」与「落在哪份文件哪一行」
    - 文件读不出或语法不通即跳过，导入那步自有交代
    """
    try:
        tree = ast.parse(file.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return None
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        for name in _imported_names(node):
            if name.partition(".")[0] in _BODY_ROOTS:
                return name, f"{file.name}:{node.lineno}"
    return None


def _imported_names(node: ast.Import | ast.ImportFrom) -> tuple[str, ...]:
    """一条导入语句交出的绝对名，相对导入没有"""
    if isinstance(node, ast.ImportFrom):
        return () if node.level or not node.module else (node.module,)
    if isinstance(node, ast.Import):
        return tuple(alias.name for alias in node.names)
    return ()
