# devtools/_style_checks/_s9_typing.py
"""类型注解分节检查

- 所有 def（含方法/异步）形参与返回值必须写注解
- __init__ 返回 -> None（ruff D 不管这里）
- 豁免：self/cls、简单 lambda、super 纯转发的 vararg/kwarg
- super().__init__(*args, **kwargs) 转发不引入 ParamSpec 提示
- `# type: ignore` 必须带 `[错误码]`，裸标记会连整行其他错误一起吞掉
"""

from __future__ import annotations

import ast
import re
from typing import TYPE_CHECKING

from ._common import Finding

if TYPE_CHECKING:
    from ._common import FileData

_EXEMPT_PARAMS: frozenset[str] = frozenset({"self", "cls"})

# 未紧跟方括号的抑制标记，缺的就是那份错误码
_BARE_IGNORE_RE = re.compile(r"type:\s*ignore(?!\s*\[)")


def check(files: list[FileData]) -> list[Finding]:
    """扫描类型注解违规"""
    findings: list[Finding] = []
    for file in files:
        if file.parse_error:
            continue
        findings.extend(_check_defs(file))
        findings.extend(_check_bare_ignores(file))
    return findings


def _check_bare_ignores(file: FileData) -> list[Finding]:
    """整行与行尾注释里的裸抑制标记"""
    findings: list[Finding] = []
    for line, text in {**file.comments, **file.eol}.items():
        if _BARE_IGNORE_RE.search(text):
            findings.append(
                _f(file, line, "`# type: ignore` 未带 `[错误码]`", hard=True)
            )
    return findings


def _check_defs(file: FileData) -> list[Finding]:
    """逐个 def 检查形参与返回注解"""
    findings: list[Finding] = []
    for node in (
        n
        for n in ast.walk(file.tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    ):
        if _is_simple_lambda_stub(node):
            continue
        args = node.args
        all_params = [*args.posonlyargs, *args.args, *args.kwonlyargs]
        if args.vararg:
            all_params.append(args.vararg)
        if args.kwarg:
            all_params.append(args.kwarg)
        for a in all_params:
            if a.arg in _EXEMPT_PARAMS:
                continue
            if a.annotation is None:
                if a in (args.vararg, args.kwarg) and _is_super_forward(node):
                    continue
                findings.append(
                    _f(
                        file,
                        node.lineno,
                        f"函数 `{node.name}` 形参 `{a.arg}` 缺类型注解",
                        hard=True,
                    ),
                )
        if node.returns is None:
            if node.name == "__init__":
                findings.append(
                    _f(file, node.lineno, "`__init__` 缺 `-> None` 返回注解", hard=True)
                )
            else:
                findings.append(
                    _f(
                        file, node.lineno, f"函数 `{node.name}` 缺返回值注解", hard=True
                    ),
                )
    return findings


def _is_super_forward(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """识别 super 纯转发"""
    for stmt in node.body:
        if not isinstance(stmt, ast.Expr) or not isinstance(stmt.value, ast.Call):
            continue
        call = stmt.value
        func = call.func
        if not (isinstance(func, ast.Attribute) and isinstance(func.value, ast.Call)):
            continue
        inner = func.value
        if (
            isinstance(inner.func, ast.Name)
            and inner.func.id == "super"
            and func.attr == "__init__"
        ):
            return True
    return False


def _is_simple_lambda_stub(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """函数体仅一条 return lambda 视为简单 lambda 豁免"""
    if len(node.body) != 1:
        return False
    stmt = node.body[0]
    if isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Lambda):
        return True
    return False


def _f(file: FileData, line: int, message: str, hard: bool) -> Finding:
    """构造本分节违规条目"""
    return Finding("类型注解", file.rel, line, message, hard)
