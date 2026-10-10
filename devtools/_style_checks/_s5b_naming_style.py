# devtools/_style_checks/_s5b_naming_style.py
"""命名风格分节检查

- 连续裸常量赋值无分组注释疑似堆积
- 同域成员不重复域前缀
- core/dto 类型一律 DTO 后缀
"""

from __future__ import annotations

import ast
import re
from typing import TYPE_CHECKING

from ._common import SECTIONS, Finding

if TYPE_CHECKING:
    from ._common import FileData

# 命名风格阈值
_SCATTER_MIN = 3  # 规范"攒够三五件即收"取下限


def check_style(files: list[FileData]) -> list[Finding]:
    """扫描单文件命名风格违规"""
    findings: list[Finding] = []
    for file in files:
        if file.parse_error:
            continue
        findings.extend(_check_scatter(file))
        findings.extend(_check_class_domain_prefix(file))
        findings.extend(_check_dto_suffix(file))
    return findings


def _check_scatter(file: FileData) -> list[Finding]:
    """连续裸常量赋值且组内无分组注释，疑似散装堆积"""
    findings: list[Finding] = []
    run: list[ast.stmt] = []
    for node in file.tree.body:
        if _is_plain_assign(node):
            run.append(node)
            continue
        if len(run) >= _SCATTER_MIN and not _run_commented(file, run):
            findings.append(_scatter_finding(file, run))
        run = []
    if len(run) >= _SCATTER_MIN and not _run_commented(file, run):
        findings.append(_scatter_finding(file, run))
    return findings


def _is_plain_assign(node: ast.stmt) -> bool:
    """单目标赋值判定"""
    if isinstance(node, ast.Assign):
        return len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
    return isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)


def _run_commented(file: FileData, run: list[ast.stmt]) -> bool:
    """连续段内或紧邻上方存在整行注释即视为已分组"""
    first, last = run[0], run[-1]
    if any(first.lineno <= line <= last.lineno for line in file.comments):
        return True
    return (first.lineno - 1) in file.comments


def _scatter_finding(file: FileData, run: list[ast.stmt]) -> Finding:
    """堆积段的首条违规描述"""
    start = run[0].lineno
    names = ", ".join(_assign_name(item) for item in run[:4])
    more = f" 等 {len(run)} 件" if len(run) > 4 else ""
    return _f(
        file,
        start,
        f"连续 {len(run)} 个裸常量赋值无分组注释（{names}{more}），攒够即收进命名空间类或分组隔开",
        hard=False,
    )


def _assign_name(node: ast.stmt) -> str:
    """取赋值目标名"""
    if isinstance(node, ast.Assign):
        target = node.targets[0]
    elif isinstance(node, ast.AnnAssign):
        target = node.target
    else:
        return "?"
    return target.id if isinstance(target, ast.Name) else "?"


def _check_class_domain_prefix(file: FileData) -> list[Finding]:
    """类成员域前缀重复检查"""
    findings: list[Finding] = []
    for node in ast.walk(file.tree):
        if not isinstance(node, ast.ClassDef):
            continue
        prefix = _camel_to_upper(node.name)
        for item in node.body:
            names: list[ast.expr] = []
            if isinstance(item, ast.Assign):
                names = list(item.targets)
            elif isinstance(item, ast.AnnAssign):
                names = [item.target]
            for t in names:
                if not isinstance(t, ast.Name) or t.id == prefix:
                    continue
                if t.id.upper().startswith(f"{prefix}_"):
                    findings.append(
                        _f(
                            file,
                            item.lineno,
                            f"类 `{node.name}` 成员 `{t.id}` 重复域前缀，应去 `{prefix}_` 头",
                            hard=True,
                        ),
                    )
    return findings


def _camel_to_upper(name: str) -> str:
    """驼峰转下划线大写"""
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", "_", name).upper()


def _check_dto_suffix(file: FileData) -> list[Finding]:
    """core/dto 下对外类型必须 DTO 后缀"""
    if not (file.module == "core.dto" or file.module.startswith("core.dto.")):
        return []
    findings: list[Finding] = []
    for node in file.tree.body:
        if isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            if not node.name.endswith("DTO"):
                findings.append(
                    _f(
                        file,
                        node.lineno,
                        f"core/dto 类 `{node.name}` 缺 DTO 后缀",
                        hard=True,
                    )
                )
    return findings


def _f(file: FileData, line: int, message: str, hard: bool) -> Finding:
    """构造本分节违规条目"""
    return Finding(SECTIONS[4], file.rel, line, message, hard)
