# devtools/_style_checks/_s3_docstring.py
"""Docstring 分节检查

- 标题行禁标点、禁括号冒号解释、禁分号
- 标题行中文逗号/顿号疑似折行
- 标题与详情间必须空一行
- 详情段一行一要点且以 `-` 起头
- 一行一句、行尾禁句号
- 缺 docstring 由 ruff 的 D 系列负责，本分节不重复扫
"""

from __future__ import annotations

import ast
import re
from typing import TYPE_CHECKING

from ._common import SECTIONS, Finding, has_cjk

if TYPE_CHECKING:
    from ._common import FileData

# docstring 文本规则
_PAREN_RE = re.compile(r"[（(）)]")
_SEMICOLON_RE = re.compile(r"[;；]")
_EOL_PERIOD_RE = re.compile(r"[。.]\s*$")
_CN_BREAK_RE = re.compile(r"[，、；;]$")


def check(files: list[FileData]) -> list[Finding]:
    """扫描 Docstring 违规"""
    findings: list[Finding] = []
    for file in files:
        if file.parse_error:
            continue
        findings.extend(_check_defs(file))
    return findings


def _check_defs(file: FileData) -> list[Finding]:
    """逐个函数/类的 docstring 文本规则检查"""
    findings: list[Finding] = []
    for node in _doc_nodes(file):
        doc_node = _docstring_node(node)
        if doc_node is None:
            continue
        findings.extend(_check_docstring_body(file, doc_node))
    return findings


def _doc_nodes(
    file: FileData,
) -> list[ast.AST]:
    """收集模块与全部函数类的文档节点"""
    nodes: list[ast.AST] = [file.tree]
    nodes += [
        item
        for item in ast.walk(file.tree)
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ]
    return nodes


def _docstring_node(node: ast.AST) -> ast.Constant | None:
    """取定义节点的 docstring 字面量"""
    body_attr = getattr(node, "body", None)
    if not body_attr:
        return None
    first = body_attr[0]
    if (
        isinstance(first, ast.Expr)
        and isinstance(first.value, ast.Constant)
        and isinstance(first.value.value, str)
    ):
        return first.value
    return None


def _check_docstring_body(file: FileData, doc: ast.Constant) -> list[Finding]:
    """检查 docstring 文本的标题行与详情段"""
    text = doc.value
    if not isinstance(text, str):
        return []
    raw_lines = text.splitlines()
    if not any(ln.strip() for ln in raw_lines):
        return [_f(file, doc.lineno, "docstring 为空", hard=False)]
    body = list(raw_lines)
    title_line = doc.lineno
    if not body[0].strip():
        body = body[1:]
        title_line = doc.lineno + 1
    findings: list[Finding] = []
    findings.extend(_check_title(file, title_line, body[0].strip()))
    findings.extend(_check_detail(file, title_line, body[1:]))
    return findings


def _check_title(file: FileData, line: int, title: str) -> list[Finding]:
    """标题行规则检查"""
    findings: list[Finding] = []
    if not title:
        return findings
    if _PAREN_RE.search(title):
        findings.append(
            _f(file, line, f"docstring 标题行含括号解释：`{title}`", hard=False)
        )
    if ":" in title or "：" in title:
        findings.append(
            _f(file, line, f"docstring 标题行含冒号解释：`{title}`", hard=False)
        )
    if _SEMICOLON_RE.search(title):
        findings.append(_f(file, line, f"docstring 标题行含分号：`{title}`", hard=True))
    if _EOL_PERIOD_RE.search(title):
        findings.append(_f(file, line, f"docstring 标题行尾句号：`{title}`", hard=True))
    if has_cjk(title) and _CN_BREAK_RE.search(title):
        findings.append(
            _f(
                file,
                line,
                f"docstring 标题行以逗号顿号结尾疑似折行：`{title}`",
                hard=False,
            )
        )
    return findings


def _check_detail(
    file: FileData, title_line: int, detail: list[str]
) -> list[Finding]:
    """详情段规则检查"""
    if not detail:
        return []
    findings: list[Finding] = []
    real = [ln for ln in detail if ln.strip()]
    if detail[0].strip():
        findings.append(
            _f(file, title_line + 1, "docstring 标题与详情之间缺空行", hard=True)
        )
    for i, line in enumerate(detail, start=1):
        stripped = line.strip().strip('"').strip("'").strip()
        if not stripped or stripped in ('"""', "'''"):
            continue
        cur = title_line + i
        if not stripped.startswith("-"):
            findings.append(
                _f(file, cur, f"docstring 详情行未以 `-` 起头：{stripped}", hard=True)
            )
        if _SEMICOLON_RE.search(stripped):
            findings.append(
                _f(file, cur, f"docstring 详情行含分号：{stripped}", hard=True)
            )
        if _EOL_PERIOD_RE.search(stripped):
            findings.append(
                _f(file, cur, f"docstring 详情行尾句号：{stripped}", hard=True)
            )
        if has_cjk(stripped) and _CN_BREAK_RE.search(stripped):
            findings.append(
                _f(
                    file,
                    cur,
                    f"docstring 详情行以逗号顿号结尾疑似折行：{stripped}",
                    hard=False,
                )
            )
    if not real:
        findings.clear()
    return findings


def _f(file: FileData, line: int, message: str, hard: bool) -> Finding:
    """构造本分节违规条目"""
    return Finding(SECTIONS[2], file.rel, line, message, hard)
