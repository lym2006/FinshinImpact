# devtools/_style_checks/_s6_magic.py
"""魔法数字与字符串分节检查

- 函数体内裸数字字面量提示提取为常量
- 豁免：-1/0/1 等哨兵值、下标、幂、端口/错误码尾数、时间单位组合
- 协议串收进命名空间类：跨文件重复出现的短字面量提示单源
- 函数体内裸定义的模块级名提示下沉
"""

from __future__ import annotations

import ast
from collections import defaultdict
from collections.abc import Sequence
from typing import TYPE_CHECKING

from ._common import SECTIONS, Finding

if TYPE_CHECKING:
    from ._common import FileData

# 数字与字符串豁免表
_SENTINELS: frozenset[int] = frozenset({-1, 0, 1, 2})
_TIME_UNITS: frozenset[int] = frozenset({60, 600, 1000, 3600, 86400})
_STR_MIN_LEN = 3
_STR_MAX_LEN = 40

# 协议串不统计的容器：类命名空间、大写常量、__all__ 导出名
_SKIP_CONTAINERS = frozenset({"class", "assign-upper", "dunder-all"})


def check(files: list[FileData]) -> list[Finding]:
    """扫描魔法数字与字符串违规"""
    findings: list[Finding] = []
    for file in files:
        if file.parse_error:
            continue
        findings.extend(_check_numbers(file))
    findings.extend(_check_protocol_strings(files))
    return findings


def _check_numbers(file: FileData) -> list[Finding]:
    """函数体内裸数字，嵌套函数只报最内层一次"""
    findings: list[Finding] = []
    class_lines = _named_assign_lines(file)
    funcs = [
        n
        for n in ast.walk(file.tree)
        if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)
    ]
    owner = _innermost_owners(funcs)
    for func in funcs:
        skip_nodes = _structural_parents(func)
        for node in ast.walk(func):
            if not isinstance(node, ast.Constant) or not isinstance(
                node.value, (int, float)
            ):
                continue
            if owner.get(id(node)) is not func:
                continue
            if node in skip_nodes or node.lineno in class_lines:
                continue
            if _exempt_number(node.value):
                continue
            findings.append(
                _f(
                    file,
                    node.lineno,
                    f"函数 `{func.name}` 内魔法数字 `{node.value}`，应提为顶部私有常量并注明换算值",
                    hard=False,
                ),
            )
    return findings


def _innermost_owners(
    funcs: Sequence[ast.FunctionDef | ast.AsyncFunctionDef],
) -> dict[int, ast.FunctionDef | ast.AsyncFunctionDef]:
    """字面量节点到最内层包含函数的映射"""
    owners: dict[int, ast.FunctionDef | ast.AsyncFunctionDef] = {}
    for func in funcs:
        for node in ast.walk(func):
            owners[id(node)] = func
    return owners


def _named_assign_lines(file: FileData) -> set[int]:
    """命名常量赋值行集合"""
    lines: set[int] = set()
    holders: list[ast.AST] = [file.tree]
    holders += [n for n in ast.walk(file.tree) if isinstance(n, ast.ClassDef)]
    for holder in holders:
        for item in getattr(holder, "body", []):
            targets: list[ast.expr] = []
            if isinstance(item, ast.Assign):
                targets = list(item.targets)
            elif isinstance(item, ast.AnnAssign):
                targets = [item.target]
            if (
                len(targets) == 1
                and isinstance(targets[0], ast.Name)
                and item.value is not None
            ):
                for node in ast.walk(item.value):
                    if isinstance(node, ast.Constant) and isinstance(
                        node.value, (int, float)
                    ):
                        lines.add(node.lineno)
    return lines


def _structural_parents(
    func: ast.FunctionDef | ast.AsyncFunctionDef,
) -> set[ast.AST]:
    """数字豁免位置收集"""
    skipped: set[ast.AST] = set()
    for node in ast.walk(func):
        if isinstance(node, ast.Subscript):
            skipped.update(_const_nodes(node.slice))
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Pow):
            skipped.update(_const_nodes(node.left))
            skipped.update(_const_nodes(node.right))
        elif isinstance(node, ast.Compare):
            for comp in node.comparators:
                skipped.update(_const_nodes(comp))
            skipped.update(_const_nodes(node.left))
        elif isinstance(node, ast.JoinedStr):
            skipped.update(_const_nodes(node))
    return skipped


def _const_nodes(root: ast.AST) -> list[ast.Constant]:
    """子树内全部数字字面量节点"""
    return [
        n
        for n in ast.walk(root)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float))
    ]


def _exempt_number(value: int | float) -> bool:
    """数字豁免判定"""
    if isinstance(value, bool):
        return True
    if value in _SENTINELS or value in _TIME_UNITS:
        return True
    if isinstance(value, int) and value >= 1024:
        return True
    return abs(value) >= 1000


def _check_protocol_strings(files: list[FileData]) -> list[Finding]:
    """跨文件重复裸字符串疑似协议串"""
    locations: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for file in files:
        if file.parse_error:
            continue
        for node in ast.walk(file.tree):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            text = node.value
            if not (_STR_MIN_LEN <= len(text) <= _STR_MAX_LEN):
                continue
            if not text.replace("_", "").replace("-", "").isalnum():
                continue
            if text.lower() in text or text != text.strip():
                continue
            holder = _parent_container(file, node)
            if holder in _SKIP_CONTAINERS:
                continue
            locations[text].append((file.rel, node.lineno))
    findings: list[Finding] = []
    for text, spots in sorted(locations.items()):
        files_hit = {rel for rel, _ in spots}
        if len(files_hit) >= 2:
            first = spots[0]
            findings.append(
                _f_by(
                    first[0],
                    first[1],
                    f"协议串疑似重复裸写 `{text}`，出现于 {len(spots)} 处，应单源收进命名空间类",
                    hard=False,
                ),
            )
    return findings


def _parent_container(file: FileData, node: ast.Constant) -> str:
    """字符串字面量所处的定义容器类型"""
    for item in file.tree.body:
        if _is_dunder_all(item) and _contains(item, node):
            return "dunder-all"
    for class_node in ast.walk(file.tree):
        if isinstance(class_node, ast.ClassDef):
            for item in class_node.body:
                # 方法体内的字符串不是类命名空间成员，不得吞成 class 容器
                if isinstance(
                    item, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
                ):
                    continue
                if _contains(item, node):
                    return "class"
    for item in file.tree.body:
        if _contains(item, node):
            if isinstance(item, ast.Assign):
                targets = item.targets
            elif isinstance(item, ast.AnnAssign):
                targets = [item.target]
            else:
                continue
            names = [t.id for t in targets if isinstance(t, ast.Name)]
            if any(
                n.isupper() or n.startswith("_") and n.lstrip("_").isupper()
                for n in names
            ):
                return "assign-upper"
    return "inline"


def _is_dunder_all(item: ast.stmt) -> bool:
    """模块级语句是否为 __all__ 赋值"""
    if isinstance(item, ast.Assign):
        targets: list[ast.expr] = list(item.targets)
    elif isinstance(item, ast.AnnAssign):
        targets = [item.target]
    else:
        return False
    return any(isinstance(t, ast.Name) and t.id == "__all__" for t in targets)


def _contains(root: ast.AST, node: ast.Constant) -> bool:
    """根节点子树是否包含目标常量节点"""
    return any(child is node for child in ast.walk(root))


def _f(file: FileData, line: int, message: str, hard: bool) -> Finding:
    """构造本分节违规条目"""
    return Finding(SECTIONS[5], file.rel, line, message, hard)


def _f_by(rel: str, line: int, message: str, hard: bool) -> Finding:
    """按相对路径构造违规条目"""
    return Finding(SECTIONS[5], rel, line, message, hard)
