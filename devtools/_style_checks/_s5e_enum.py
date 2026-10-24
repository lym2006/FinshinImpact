# devtools/_style_checks/_s5e_enum.py
"""枚举分节检查

- 枚举基类须为值型 StrEnum/IntEnum
- IntEnum 成员值须互不相等且随定义顺序严格递增
- auto() 成员提示人工确认参与大小比较的枚举已写死数字
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

from ._common import Finding

if TYPE_CHECKING:
    from ._common import FileData

_VALUE_BASES: frozenset[str] = frozenset({"StrEnum", "IntEnum"})
_ALL_BASES: frozenset[str] = _VALUE_BASES | {"Enum", "Flag", "IntFlag"}


def check(files: list[FileData]) -> list[Finding]:
    """扫描枚举定义违规"""
    findings: list[Finding] = []
    for file in files:
        if file.parse_error:
            continue
        for node in file.tree.body:
            if isinstance(node, ast.ClassDef):
                findings.extend(_check_class(file, node))
    return findings


def _check_class(file: FileData, node: ast.ClassDef) -> list[Finding]:
    """单个类定义的枚举检查，值型基类再查成员值"""
    bases = {_base_name(base) for base in node.bases}
    if bases & _ALL_BASES:
        if not bases & _VALUE_BASES:
            return [
                _f(
                    file,
                    node.lineno,
                    f"枚举 `{node.name}` 基类非值型，应改用 StrEnum 或 IntEnum",
                    hard=True,
                )
            ]
        if "IntEnum" in bases:
            return _check_int_values(file, node)
        return []
    for sub in node.body:
        if isinstance(sub, ast.ClassDef):
            return _check_class(file, sub)
    return []


def _check_int_values(file: FileData, node: ast.ClassDef) -> list[Finding]:
    """IntEnum 成员值互不相等且随定义顺序严格递增"""
    findings: list[Finding] = []
    previous: int | None = None
    for item in node.body:
        if not isinstance(item, ast.Assign) or not isinstance(item.value, ast.expr):
            continue
        name = next(
            (t.id for t in item.targets if isinstance(t, ast.Name) and t.id.isupper()),
            "",
        )
        if not name:
            continue
        value = item.value
        if _is_auto(value):
            findings.append(
                _f(
                    file,
                    item.lineno,
                    f"`{node.name}.{name}` 用 auto()，参与大小比较须改写成死数字",
                    hard=False,
                )
            )
            continue
        number = _int_literal(value)
        if number is None:
            continue
        if previous is not None and number <= previous:
            relation = "重号" if number == previous else "未严格递增"
            findings.append(
                _f(
                    file,
                    item.lineno,
                    f"`{node.name}.{name}` 值 {number} 与前值 {previous} 相比{relation}，重号即静默别名",
                    hard=True,
                )
            )
        previous = number
    return findings


def _base_name(base: ast.expr) -> str:
    """基类表达式取末段名"""
    if isinstance(base, ast.Name):
        return base.id
    if isinstance(base, ast.Attribute):
        return base.attr
    return ""


def _is_auto(value: ast.expr) -> bool:
    return isinstance(value, ast.Call) and _base_name(value.func) == "auto"


def _int_literal(value: ast.expr) -> int | None:
    """整数字面量取值，bool 视同非法值返回 None"""
    if isinstance(value, ast.UnaryOp) and isinstance(value.op, ast.USub):
        inner = _int_literal(value.operand)
        return -inner if inner is not None else None
    if isinstance(value, ast.Constant) and isinstance(value.value, int):
        if isinstance(value.value, bool):
            return None
        return value.value
    return None


def _f(file: FileData, line: int, message: str, hard: bool) -> Finding:
    """构造枚举分节违规条目"""
    return Finding("枚举", file.rel, line, message, hard)
