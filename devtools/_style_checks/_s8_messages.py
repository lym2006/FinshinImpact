# devtools/_style_checks/_s8_messages.py
"""messages 包文案类分节检查

- 每域一个类 XxxMessage
- 域文件仅门面导入属内部实现，文件名带 `_` 且为类名 snake_case
- 类名已含域义则成员不再重复域前缀
- 每条成员行首注释标注使用位置
- 跨域同义文案单源：相同中文文案多文件出现提示
"""

from __future__ import annotations

import ast
import re
from collections import defaultdict
from typing import TYPE_CHECKING

from ._common import SECTIONS, Finding, has_cjk

if TYPE_CHECKING:
    from ._common import FileData

_MESSAGES_PACKAGE = "messages"


def check(files: list[FileData]) -> list[Finding]:
    """扫描文案类违规"""
    findings: list[Finding] = []
    msg_files = [f for f in files if f.package == _MESSAGES_PACKAGE and not f.is_init]
    texts: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for file in msg_files:
        if file.parse_error:
            continue
        classes = [n for n in file.tree.body if isinstance(n, ast.ClassDef)]
        findings.extend(_check_file_naming(file, classes))
        findings.extend(_check_members(file, classes))
        for cls in classes:
            for text, line in _class_str_values(file, cls):
                texts[text].append((file.rel, line))
    for text, spots in sorted(texts.items()):
        hit_files = sorted({rel for rel, _ in spots})
        if len(hit_files) >= 2:
            rel, line = spots[0]
            findings.append(
                Finding(
                    SECTIONS[7],
                    rel,
                    line,
                    f"跨域同义文案 `{text[:24]}…` 出现在 {len(hit_files)} 个文件，应单源一处定义",
                    False,
                ),
            )
    return findings


def _check_file_naming(file: FileData, classes: list[ast.ClassDef]) -> list[Finding]:
    """域文件命名检查"""
    findings: list[Finding] = []
    if len(classes) > 1:
        joined = ", ".join(c.name for c in classes)
        findings.append(
            _f(
                file,
                classes[1].lineno,
                f"文案域文件含 {len(classes)} 个类（{joined}），规范要求每域一个类",
                hard=False,
            )
        )
    if not classes:
        return findings
    expected = f"_{_snake(classes[0].name)}"
    if classes[0].name.endswith("Message"):
        expected = f"_{_snake(classes[0].name[: -len('Message')])}"
    if not file.stem.startswith("_"):
        findings.append(
            _f(
                file,
                1,
                f"文案域文件 `{file.path.name}` 应带 `_` 前缀（仅门面导入属内部实现）",
                hard=True,
            )
        )
    if file.stem.lstrip("_") != expected.lstrip("_"):
        findings.append(
            _f(file, 1, f"文案域文件名与类名不匹配，期望 `{expected}.py`", hard=True)
        )
    return findings


def _check_members(file: FileData, classes: list[ast.ClassDef]) -> list[Finding]:
    """成员使用位置注释 + 不重复域前缀"""
    findings: list[Finding] = []
    for cls in classes:
        domain = (
            cls.name[: -len("Message")] if cls.name.endswith("Message") else cls.name
        )
        prefix = _camel_to_upper(domain)
        members = _member_items(cls)
        for idx, (item, name_node) in enumerate(members):
            if name_node.id.upper().startswith(f"{prefix}_") and name_node.id != prefix:
                findings.append(
                    _f(
                        file,
                        item.lineno,
                        f"类 `{cls.name}` 成员 `{name_node.id}` 重复域前缀，应去 `{prefix}_` 头",
                        hard=True,
                    ),
                )
            if not _group_commented(file, cls, members, idx):
                findings.append(
                    _f(
                        file,
                        item.lineno,
                        f"文案成员 `{name_node.id}` 所在组缺使用位置注释",
                        hard=False,
                    ),
                )
    return findings


def _member_items(cls: ast.ClassDef) -> list[tuple[ast.stmt, ast.Name]]:
    """类内命名成员收集"""
    results: list[tuple[ast.stmt, ast.Name]] = []
    for item in cls.body:
        if isinstance(item, ast.Expr):
            continue
        targets: list[ast.expr] = []
        if isinstance(item, ast.Assign):
            targets = list(item.targets)
        elif isinstance(item, ast.AnnAssign):
            targets = [item.target]
        for t in targets:
            if isinstance(t, ast.Name) and not t.id.startswith("__"):
                results.append((item, t))
    return results


def _group_commented(
    file: FileData,
    cls: ast.ClassDef,
    members: list[tuple[ast.stmt, ast.Name]],
    idx: int,
) -> bool:
    """成员组注释覆盖判定"""
    item = members[idx][0]
    prev_end = cls.lineno
    if idx > 0:
        prev = members[idx - 1][0]
        prev_end = prev.end_lineno or prev.lineno
        if prev_end == item.lineno - 1 and _group_commented(
            file, cls, members, idx - 1
        ):
            return True
    return any(prev_end < line < item.lineno for line in file.comments)


def _class_str_values(file: FileData, cls: ast.ClassDef) -> list[tuple[str, int]]:
    """类内字符串常量收集"""
    results: list[tuple[str, int]] = []
    for item in cls.body:
        value = item.value if isinstance(item, (ast.Assign, ast.AnnAssign)) else None
        if (
            isinstance(value, ast.Constant)
            and isinstance(value.value, str)
            and has_cjk(value.value)
        ):
            results.append((value.value, item.lineno))
    return results


def _snake(name: str) -> str:
    """驼峰转下划线"""
    return _camel_to_upper(name).lower()


def _camel_to_upper(name: str) -> str:
    """驼峰转下划线大写"""
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", "_", name).upper()


def _f(file: FileData, line: int, message: str, hard: bool) -> Finding:
    """构造本分节违规条目"""
    return Finding(SECTIONS[7], file.rel, line, message, hard)
