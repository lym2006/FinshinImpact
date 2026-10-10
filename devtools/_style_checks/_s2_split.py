# devtools/_style_checks/_s2_split.py
"""拆分粒度分节检查

- 单文件超 300 行触发拆分评审
- 同族顶层函数超 6 个触发拆分评审
- 单类方法超 10 个触发拆分评审
- 单函数体超 60 行评审、超 80 行硬拆
"""

from __future__ import annotations

import ast
from collections import defaultdict
from typing import TYPE_CHECKING

from ._common import SECTIONS, Finding

if TYPE_CHECKING:
    from ._common import FileData

# 拆分粒度阈值
_FILE_MAX_LINES = 300
_TOP_FUNC_MAX = 6
_CLASS_METHOD_MAX = 10
_BODY_REVIEW_LINES = 60
_BODY_HARD_LINES = 80


def check(files: list[FileData]) -> list[Finding]:
    """扫描拆分粒度违规"""
    findings: list[Finding] = []
    for file in files:
        if file.parse_error:
            continue
        findings.extend(_check_file(file))
        findings.extend(_check_functions(file))
        findings.extend(_check_classes(file))
    return findings


def _check_file(file: FileData) -> list[Finding]:
    """文件级触发线"""
    findings: list[Finding] = []
    total = len(file.lines)
    if total > _FILE_MAX_LINES:
        findings.append(
            _f(
                file,
                total,
                f"单文件 {total} 行，超 {_FILE_MAX_LINES} 行触发线",
                hard=False,
            )
        )
    family = _top_func_family(file)
    for name, count in family.items():
        if count > _TOP_FUNC_MAX:
            findings.append(
                _f(
                    file,
                    _family_anchor(file, name),
                    f"同族顶层函数 `{name}*` 共 {count} 个，超 {_TOP_FUNC_MAX} 个触发线",
                    hard=False,
                ),
            )
    return findings


def _top_func_family(file: FileData) -> dict[str, int]:
    """按首段词根给顶层函数分族计数"""
    counter: dict[str, int] = defaultdict(int)
    for node in file.tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            counter[_word_root(node.name)] += 1
    return dict(counter)


def _family_anchor(file: FileData, root: str) -> int:
    """同族首个函数的行号"""
    for node in file.tree.body:
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and _word_root(node.name) == root
        ):
            return node.lineno
    return 1


def _word_root(name: str) -> str:
    """取函数名第一个词根作族名"""
    stripped = name.lstrip("_")
    head = stripped.split("_")[0]
    return head.lower()


def _check_functions(file: FileData) -> list[Finding]:
    """函数体行数触发线"""
    findings: list[Finding] = []
    for node in _all_funcs(file.tree):
        span = _body_span(node)
        if span > _BODY_HARD_LINES:
            findings.append(
                _f(
                    file,
                    node.lineno,
                    f"函数 `{node.name}` 体 {span} 行，超 {_BODY_HARD_LINES} 行硬拆线",
                    hard=True,
                )
            )
        elif span > _BODY_REVIEW_LINES:
            findings.append(
                _f(
                    file,
                    node.lineno,
                    f"函数 `{node.name}` 体 {span} 行，超 {_BODY_REVIEW_LINES} 行评审线",
                    hard=False,
                )
            )
    return findings


def _check_classes(file: FileData) -> list[Finding]:
    """单类方法数触发线"""
    findings: list[Finding] = []
    for node in ast.walk(file.tree):
        if not isinstance(node, ast.ClassDef):
            continue
        methods = [
            m
            for m in node.body
            if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        if len(methods) > _CLASS_METHOD_MAX:
            findings.append(
                _f(
                    file,
                    node.lineno,
                    f"类 `{node.name}` 方法 {len(methods)} 个，超 {_CLASS_METHOD_MAX} 个触发线",
                    hard=False,
                ),
            )
    return findings


def _all_funcs(tree: ast.Module) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    """收集全部函数定义"""
    return [
        n
        for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]


def _body_span(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """函数体有效行数"""
    body = list(node.body)
    if body and _is_docstring(body[0]):
        body.pop(0)
    if not body:
        return 0
    first, last = body[0], body[-1]
    return (last.end_lineno or last.lineno) - first.lineno + 1


def _is_docstring(node: ast.stmt) -> bool:
    """判断语句是否为 docstring"""
    return (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )


def _f(file: FileData, line: int, message: str, hard: bool) -> Finding:
    """构造本分节违规条目"""
    return Finding(SECTIONS[1], file.rel, line, message, hard)
