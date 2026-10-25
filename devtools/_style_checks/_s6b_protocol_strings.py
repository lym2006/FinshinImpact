# devtools/_style_checks/_s6b_protocol_strings.py
"""协议串分节细则

- 跨文件重复短字面量提示单源收进命名空间类
- 注解位字符串与 get_logger 域名实参不计入协议串
- 类命名空间、大写常量、__all__ 导出位不计
"""

from __future__ import annotations

import ast
from collections import defaultdict
from typing import TYPE_CHECKING

from ._common import Finding

if TYPE_CHECKING:
    from ._common import FileData

# 协议串判定参数
_STR_MIN_LEN = 3
_STR_MAX_LEN = 40

# 协议串不统计的容器：类命名空间、大写常量、__all__ 导出名
_SKIP_CONTAINERS = frozenset({"class", "assign-upper", "dunder-all"})

# 日志域名入口函数，其实参字符串不计协议串
_LOGGER_FUNC = "get_logger"


def check_strings(files: list[FileData]) -> list[Finding]:
    """扫描跨文件重复协议串"""
    locations: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for file in files:
        if file.parse_error:
            continue
        skipped = _non_protocol_nodes(file)
        for node in ast.walk(file.tree):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            if id(node) in skipped:
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


def _non_protocol_nodes(file: FileData) -> set[int]:
    """不计入协议串的字符串节点 id 集

    - 注解位字符串是类型引用不是协议值
    - get_logger 实参是日志域名，多处同名属设计意图
    """
    skipped: set[int] = set()
    for node in ast.walk(file.tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            for arg in _all_args(node.args):
                _mark_strings(arg.annotation, skipped)
            _mark_strings(node.returns, skipped)
        elif isinstance(node, ast.AnnAssign):
            _mark_strings(node.annotation, skipped)
        elif isinstance(node, ast.ClassDef):
            for base in node.bases:
                _mark_strings(base, skipped)
        elif isinstance(node, ast.Call) and _is_logger_call(node):
            for arg in node.args:
                _mark_str(arg, skipped)
            for kw in node.keywords:
                _mark_str(kw.value, skipped)
    return skipped


def _all_args(args: ast.arguments) -> list[ast.arg]:
    """位置、关键字、星号形参全收集，默认值不在其中"""
    return [
        *args.posonlyargs,
        *args.args,
        *([args.vararg] if args.vararg else []),
        *args.kwonlyargs,
        *([args.kwarg] if args.kwarg else []),
    ]


def _mark_strings(root: ast.AST | None, out: set[int]) -> None:
    """子树内全部字符串常量入排除集"""
    if root is None:
        return
    for node in ast.walk(root):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            out.add(id(node))


def _mark_str(node: ast.expr, out: set[int]) -> None:
    """直挂实参为字符串常量才入排除集"""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        out.add(id(node))


def _is_logger_call(node: ast.Call) -> bool:
    """日志域名入口调用判定

    - 裸装饰器形态的同名属性访问取不到函数名，判 False
    """
    func = node.func
    name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
    return name == _LOGGER_FUNC


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


def _f_by(rel: str, line: int, message: str, hard: bool) -> Finding:
    """按相对路径构造违规条目"""
    return Finding("魔法数字与字符串", rel, line, message, hard)
