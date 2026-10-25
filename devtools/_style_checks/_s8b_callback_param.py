# devtools/_style_checks/_s8b_callback_param.py
"""回调形参分节检查

- 协程里带 `Message` 注解的形参即框架按位置注入的原始事件，名字须为 `raw`
- 注解被泛型包住的（`Awaitable[Message]`）属业务传参，不在本节口径
- 同步函数收 `Message` 属业务传参，同样不查
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

from ._common import Finding

if TYPE_CHECKING:
    from ._common import FileData

_RAW_PARAM = "raw"

# aiogram 注入的原始事件类型名，含 types.Message 属性写法
_EVENT_TYPES: frozenset[str] = frozenset({"Message"})


def check(files: list[FileData]) -> list[Finding]:
    """扫描协程形参的事件注入命名违规"""
    findings: list[Finding] = []
    for file in files:
        if file.parse_error:
            continue
        for node in ast.walk(file.tree):
            if isinstance(node, ast.AsyncFunctionDef):
                findings.extend(_check_func(file, node))
    return findings


def _check_func(file: FileData, node: ast.AsyncFunctionDef) -> list[Finding]:
    """单个协程逐形参判注入事件名"""
    findings: list[Finding] = []
    for arg in (*node.args.posonlyargs, *node.args.args):
        if _is_event_arg(arg.annotation) and arg.arg != _RAW_PARAM:
            findings.append(
                _f(
                    file,
                    arg.lineno,
                    f"协程 `{node.name}` 的注入形参 `{arg.arg}` 应改名 `{_RAW_PARAM}`",
                    hard=True,
                )
            )
    return findings


def _is_event_arg(annotation: ast.expr | None) -> bool:
    """注解本体为 Message 或其可选写法即框架注入的原始事件，泛型包住的不算"""
    if annotation is None:
        return False
    if isinstance(annotation, ast.BinOp):
        return _is_event_arg(annotation.left) or _is_event_arg(annotation.right)
    return (isinstance(annotation, ast.Name) and annotation.id in _EVENT_TYPES) or (
        isinstance(annotation, ast.Attribute) and annotation.attr in _EVENT_TYPES
    )


def _f(file: FileData, line: int, message: str, hard: bool) -> Finding:
    """生成一条回调形参违规"""
    return Finding("回调形参", file.rel, line, message, hard)
