# devtools/_style_checks/_s10_import_direction.py
"""导入方向分节检查

- 同顶层包内一律相对，绝对导入首段等于本模块顶层包即违规
- 跨层级从父包门面取符号（from .. import x）即违规，兄弟模块应直连
- gui 子树暂免，待 UI 归一迁移完成后随目录消失自动失效
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

from ._common import SECTIONS, Finding

if TYPE_CHECKING:
    from ._common import FileData

# 迁移中的过渡豁免：路径前缀命中即跳过同包绝对检查，目录清空后自动失效
_TRANSITIONAL_EXEMPT: tuple[str, ...] = ("src/gui/",)


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
    exempt = file.rel.startswith(_TRANSITIONAL_EXEMPT)
    for node in ast.walk(file.tree):
        if isinstance(node, ast.Import):
            if not exempt:
                findings.extend(_plain_violations(file, node, top))
        elif isinstance(node, ast.ImportFrom):
            findings.extend(_from_violation(file, node, top, exempt))
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


def _from_violation(
    file: FileData, node: ast.ImportFrom, top: str, exempt: bool
) -> list[Finding]:
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
    if node.module and not exempt and node.module.split(".")[0] == top:
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
    return Finding(SECTIONS[9], file.rel, line, message, hard)
