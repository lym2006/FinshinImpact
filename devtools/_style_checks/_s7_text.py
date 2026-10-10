# devtools/_style_checks/_s7_text.py
"""日志与文案分节检查

- GUI 可见文案收敛进 src/messages/，gui 下 f-string 裸写业务话术提示
- Bot 对话话术收敛进 plugins/messages.py，插件内长中文提示裸写提示
- 运行日志不收敛：logger/print 调用内中文不报
- _theme 令牌文件禁持有话术字面量
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

from ._common import SECTIONS, Finding, has_cjk

if TYPE_CHECKING:
    from ._common import FileData

# 运行日志豁免：标准 logging 级别 + 双规日志器的面板发送方法
_GUI_LOG_CALLS: frozenset[str] = frozenset(
    {
        "info",
        "warning",
        "error",
        "debug",
        "exception",
        "critical",
        "log",
        "print",
        "send_error",
    }
)
_MIN_BUSINESS_LEN = 6


def check(files: list[FileData]) -> list[Finding]:
    """扫描日志与文案违规"""
    findings: list[Finding] = []
    for file in files:
        if file.parse_error:
            continue
        if file.module.startswith("gui"):
            findings.extend(_check_gui_text(file))
        if file.module.startswith("plugins") and file.rel not in (
            "src/plugins/messages.py",
        ):
            findings.extend(_check_bot_text(file))
        if file.module.startswith("gui._theme"):
            findings.extend(_check_theme_tokens(file))
    return findings


def _log_call_lines(file: FileData) -> set[int]:
    """logger/print 调用覆盖的行号区间"""
    ranges: list[tuple[int, int]] = []
    for node in ast.walk(file.tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute):
            if func.attr in _GUI_LOG_CALLS:
                ranges.append((node.lineno, node.end_lineno or node.lineno))
        elif isinstance(func, ast.Name) and func.id in _GUI_LOG_CALLS:
            ranges.append((node.lineno, node.end_lineno or node.lineno))
    covered: set[int] = set()
    for start, end in ranges:
        covered |= set(range(start, end + 1))
    return covered


def _string_nodes(file: FileData) -> list[tuple[ast.Constant, str]]:
    """文件中全部字符串字面量节点及其文本"""
    results: list[tuple[ast.Constant, str]] = []
    for n in ast.walk(file.tree):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            results.append((n, n.value))
    return results


def _check_gui_text(file: FileData) -> list[Finding]:
    """GUI 裸写业务话术检查"""
    log_lines = _log_call_lines(file)
    doc_lines = _docstring_lines(file)
    findings: list[Finding] = []
    for node, text in _string_nodes(file):
        if node.lineno in log_lines or node.lineno in doc_lines:
            continue
        if not has_cjk(text) or len(text) < _MIN_BUSINESS_LEN:
            continue
        if _in_fstring(file, node):
            findings.append(
                _f(
                    file,
                    node.lineno,
                    f"GUI 内 f-string 裸写业务话术：`{text[:30]}…`，应收敛进 src/messages/",
                    hard=False,
                ),
            )
        else:
            findings.append(
                _f(
                    file,
                    node.lineno,
                    f"GUI 内裸写业务话术：`{text[:30]}…`，应收敛进 src/messages/",
                    hard=False,
                ),
            )
    return findings


def _check_bot_text(file: FileData) -> list[Finding]:
    """插件裸写对话话术检查"""
    log_lines = _log_call_lines(file)
    doc_lines = _docstring_lines(file)
    findings: list[Finding] = []
    for node, text in _string_nodes(file):
        if node.lineno in log_lines or node.lineno in doc_lines:
            continue
        if not has_cjk(text) or len(text) < 10:
            continue
        if "？" in text or "！" in text or "。" in text:
            findings.append(
                _f(
                    file,
                    node.lineno,
                    f"插件内裸写对话话术：`{text[:30]}…`，应收敛进 BotMessage",
                    hard=False,
                ),
            )
    return findings


def _check_theme_tokens(file: FileData) -> list[Finding]:
    """_theme 令牌只代理引用，不持有话术字面量"""
    doc_lines = _docstring_lines(file)
    findings: list[Finding] = []
    for node, text in _string_nodes(file):
        if node.lineno in doc_lines:
            continue
        if has_cjk(text) and len(text) >= 4:
            findings.append(
                _f(
                    file,
                    node.lineno,
                    f"主题令牌文件持有话术字面量：`{text[:30]}…`",
                    hard=False,
                )
            )
    return findings


def _docstring_lines(file: FileData) -> set[int]:
    """全部 docstring 覆盖的行号"""
    covered: set[int] = set()
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
            covered |= set(range(first.lineno, (first.end_lineno or first.lineno) + 1))
    return covered


def _in_fstring(file: FileData, node: ast.Constant) -> bool:
    """f-string 归属判定"""
    for joined in (n for n in ast.walk(file.tree) if isinstance(n, ast.JoinedStr)):
        for child in ast.walk(joined):
            if child is node:
                return True
    return False


def _f(file: FileData, line: int, message: str, hard: bool) -> Finding:
    """构造本分节违规条目"""
    return Finding(SECTIONS[6], file.rel, line, message, hard)
