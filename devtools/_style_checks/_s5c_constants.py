# devtools/_style_checks/_s5c_constants.py
"""模块级常量命名检查

- 无人导入且未进 __all__ 的大写常量应加 `_` 前缀
- 模块级私有变量应加 `_` 前缀或收进命名空间类
- getattr 动态消费名视同消费者
"""

from __future__ import annotations

import ast
import re
from typing import TYPE_CHECKING

from ._common import SECTIONS, Finding, ImportGraph, all_names

if TYPE_CHECKING:
    from ._common import FileData

# 常量命名样式
_UPPER_CONST_RE = re.compile(r"^_?[A-Z][A-Z0-9]*(_[A-Z0-9]+)*$")
_SNAKE_VAR_RE = re.compile(r"^_?[a-z][a-z0-9]*(_[a-z0-9]+)*$")


def check_constants(
    file: FileData, graph: ImportGraph, dynamic: set[str]
) -> list[Finding]:
    """模块级常量/变量的命名风格与前缀"""
    findings: list[Finding] = []
    usage = graph.consumers.get(file.module, {})
    imported_names: set[str] = set()
    for symbols in usage.values():
        imported_names |= {s for s in symbols if s}
    exported = all_names(file)
    for node in file.tree.body:
        targets: list[ast.expr] = []
        if isinstance(node, ast.Assign):
            targets = list(node.targets)
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        for t in targets:
            if not isinstance(t, ast.Name):
                continue
            name = t.id
            if name.startswith("__") or name == "__all__":
                continue
            if _is_type_var(node):
                continue
            if _UPPER_CONST_RE.match(name):
                if (
                    name not in imported_names
                    and name not in exported
                    and name not in dynamic
                    and not name.startswith("_")
                ):
                    findings.append(
                        _f(
                            file,
                            node.lineno,
                            f"模块级常量 `{name}` 无人导入且未进 __all__，应加 `_` 前缀",
                            hard=False,
                        ),
                    )
            elif _SNAKE_VAR_RE.match(name):
                if (
                    not name.startswith("_")
                    and name not in imported_names
                    and name not in exported
                    and name not in dynamic
                ):
                    findings.append(
                        _f(
                            file,
                            node.lineno,
                            f"模块级私有量 `{name}` 应加 `_` 前缀或收进命名空间类",
                            hard=False,
                        ),
                    )
    return findings


def _is_type_var(node: ast.stmt) -> bool:
    """赋值右侧是否为 TypeVar/NewVar/ParamSpec 构造"""
    value = node.value if isinstance(node, (ast.Assign, ast.AnnAssign)) else None
    if not isinstance(value, ast.Call):
        return False
    func = value.func
    name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
    return name in {"TypeVar", "NewType", "ParamSpec", "TypeAliasType"}


def _f(file: FileData, line: int, message: str, hard: bool) -> Finding:
    """构造命名分节违规条目"""
    return Finding(SECTIONS[4], file.rel, line, message, hard)
