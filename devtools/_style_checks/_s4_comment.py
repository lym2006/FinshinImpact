# devtools/_style_checks/_s4_comment.py
"""注释分节检查

- 函数与类定义前的前置注释一律判违规，归属不清
- 整行注释紧贴所描述代码，中间不空行
- 整行注释上方空一行（多行注释非首行、块首之后、docstring 之后、__all__ 内部豁免）
- 两行整行注释之间不许空行分隔，禁悬空标题
- 注释行禁分号、禁逗号顿号劈行
"""

from __future__ import annotations

import ast
import re
from typing import TYPE_CHECKING

from ._common import SECTIONS, Finding, has_cjk

if TYPE_CHECKING:
    from ._common import FileData

# 注释文本规则
_BLOCK_END_RE = re.compile(r"[:(\[{,]\s*$")
_SEMICOLON_RE = re.compile(r"[;；]")
_CN_BREAK_RE = re.compile(r"[，、；;]$")
_QUOTED_RE = re.compile(r'"[^"]*"|\'[^\']*\'')


def check(files: list[FileData]) -> list[Finding]:
    """扫描注释违规"""
    findings: list[Finding] = []
    for file in files:
        if file.parse_error:
            continue
        findings.extend(_check_leading(file))
        findings.extend(_check_spacing(file))
        findings.extend(_check_dangling(file))
        findings.extend(_check_text(file))
    return findings


def _def_lines(file: FileData) -> set[int]:
    """全部函数/类定义行与其装饰器行"""
    lines: set[int] = set()
    for node in ast.walk(file.tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            lines.add(node.lineno)
            for dec in node.decorator_list:
                lines.add(dec.lineno)
    return lines


def _check_leading(file: FileData) -> list[Finding]:
    """函数与类定义前的前置注释一律判违规"""
    findings: list[Finding] = []
    def_lines = _def_lines(file)
    for line in sorted(file.comments):
        nxt = line + 1
        if nxt in file.comments or nxt not in def_lines:
            continue
        findings.append(
            _f(
                file,
                line,
                f"定义前置注释 `# {file.comments[line]}`，归属不清，"
                "应拆类拆文件、写进该定义自身 docstring、或下沉到函数体内",
                hard=False,
            ),
        )
    return findings


def _all_range(file: FileData) -> tuple[int, int] | None:
    """__all__ 赋值的行区间"""
    for node in file.tree.body:
        names: list[ast.expr] = []
        if isinstance(node, ast.Assign):
            names = list(node.targets)
        elif isinstance(node, ast.AnnAssign):
            names = [node.target]
        if any(isinstance(t, ast.Name) and t.id == "__all__" for t in names):
            return node.lineno, node.end_lineno or node.lineno
    return None


def _docstring_ranges(file: FileData) -> set[int]:
    """所有 docstring 的结束行号集合"""
    ends: set[int] = set()
    holders: list[ast.AST] = [file.tree]
    holders += [
        n
        for n in ast.walk(file.tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ]
    for holder in holders:
        body = getattr(holder, "body", None)
        if not body:
            continue
        first = body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            ends.add(first.end_lineno or first.lineno)
    return ends


def _check_spacing(file: FileData) -> list[Finding]:
    """整行注释与描述代码之间的空行规则"""
    findings: list[Finding] = []
    doc_ends = _docstring_ranges(file)
    all_rng = _all_range(file)
    comment_lines = sorted(file.comments)
    comment_set = set(comment_lines)
    for line in comment_lines:
        prev = line - 1
        block_first = prev not in comment_set
        if block_first:
            in_all = all_rng and all_rng[0] <= prev <= all_rng[1]
            exempt = (
                prev in doc_ends
                or in_all
                or (prev >= 1 and _BLOCK_END_RE.search(file.lines[prev - 1]))
                or not file.lines[prev - 1].strip()
            )
            if not exempt and prev >= 1:
                findings.append(_f(file, line, "整行注释上方缺空行", hard=False))
        target = _next_code_line(file, line, comment_set)
        if (
            target is not None
            and target - line > 1
            and not _leads_comment_block(file, line, comment_set)
        ):
            findings.append(
                _f(
                    file,
                    line,
                    f"整行注释与所描述代码（第 {target} 行）之间有空行",
                    hard=True,
                ),
            )
    return findings


def _leads_comment_block(file: FileData, line: int, comment_set: set[int]) -> bool:
    """组名领起整块的豁免判定"""
    nxt = line + 1
    while nxt <= len(file.lines) and not file.lines[nxt - 1].strip():
        nxt += 1
    if nxt > len(file.lines):
        return True
    if nxt in comment_set:
        return True
    code_line = _next_code_line(file, line, comment_set)
    if code_line is not None and (code_line - 1) in comment_set:
        return True
    return False


def _check_dangling(file: FileData) -> list[Finding]:
    """两行整行注释之间不许空行分隔"""
    findings: list[Finding] = []
    comment_set = set(file.comments)
    for line in sorted(file.comments):
        nxt = line + 1
        if nxt > len(file.lines) or file.lines[nxt - 1].strip():
            continue
        while nxt <= len(file.lines) and not file.lines[nxt - 1].strip():
            nxt += 1
        if nxt <= len(file.lines) and nxt in comment_set:
            findings.append(
                _f(
                    file,
                    line,
                    "整行注释悬空，与下一条注释之间隔了空行，应紧贴所描述代码或删除",
                    hard=True,
                )
            )
    return findings


def _next_code_line(file: FileData, line: int, comment_set: set[int]) -> int | None:
    """注释块之后第一行非空代码行号"""
    cur = line
    while cur + 1 <= len(file.lines):
        cur += 1
        if cur in comment_set:
            continue
        if file.lines[cur - 1].strip():
            return cur
    return None


def _check_text(file: FileData) -> list[Finding]:
    """注释文本禁分号、禁折行"""
    findings: list[Finding] = []
    for line, text in sorted(file.comments.items()):
        bare = _QUOTED_RE.sub("", text)
        if _SEMICOLON_RE.search(bare):
            findings.append(_f(file, line, f"注释含分号：`{text}`", hard=True))
        if has_cjk(text) and _CN_BREAK_RE.search(text):
            findings.append(
                _f(file, line, f"注释以逗号顿号结尾疑似折行：`{text}`", hard=False)
            )
    return findings


def _f(file: FileData, line: int, message: str, hard: bool) -> Finding:
    """构造本分节违规条目"""
    return Finding(SECTIONS[3], file.rel, line, message, hard)
