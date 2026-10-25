# devtools/_style_checks/_s10_import_direction.py
"""导入方向分节检查

- 同顶层包内一律相对，绝对导入首段等于本模块顶层包即违规
- 跨层级从父包门面取符号（from .. import x）即违规，兄弟模块应直连
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

from ._common import Finding

if TYPE_CHECKING:
    from ._common import FileData


def check(files: list[FileData]) -> list[Finding]:
    """扫描导入方向违规"""
    findings: list[Finding] = []
    for file in files:
        if file.parse_error or not file.module:
            continue
        findings.extend(_check_file(file))
    return findings


def _check_file(file: FileData) -> list[Finding]:
    """单文件内逐条导入做方向判定"""
    top = file.module.split(".")[0]
    findings: list[Finding] = []
    for node in ast.walk(file.tree):
        if isinstance(node, ast.Import):
            findings.extend(_plain_violations(file, node, top))
        elif isinstance(node, ast.ImportFrom):
            findings.extend(_from_violation(file, node, top))
    return findings


def _plain_violations(file: FileData, node: ast.Import, top: str) -> list[Finding]:
    """import a.b 形式的同包绝对判定"""
    findings: list[Finding] = []
    for alias in node.names:
        if alias.name.split(".")[0] == top:
            findings.append(
                _f(
                    file,
                    node.lineno,
                    f"同包绝对导入 `{alias.name}`，应改用相对导入",
                    hard=True,
                )
            )
    return findings


def _from_violation(file: FileData, node: ast.ImportFrom, top: str) -> list[Finding]:
    """from x import y 形式，先判相对层级再判同包绝对"""
    if node.level:
        if node.module is None and node.level >= 2:
            return [
                _f(
                    file,
                    node.lineno,
                    "跨层级从父包门面取符号，应直连具体兄弟模块",
                    hard=True,
                )
            ]
        return []
    if node.module and node.module.split(".")[0] == top:
        return [
            _f(
                file,
                node.lineno,
                f"同包绝对导入 `{node.module}`，应改用相对导入",
                hard=True,
            )
        ]
    return []


def _f(file: FileData, line: int, message: str, hard: bool) -> Finding:
    """构造本分节违规条目"""
    return Finding("导入", file.rel, line, message, hard)
