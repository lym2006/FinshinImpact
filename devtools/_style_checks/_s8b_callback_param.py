# devtools/_style_checks/_s8b_callback_param.py
"""回调形参分节检查

- 协程里带 `Message` 注解的形参即框架按位置注入的原始事件，名字须为 `raw` 且占首位
- 注解为 `HandlerContext` 的形参按名注入，改名即取不到上下文
- 中间件的 `__call__` 由框架全位置调用，三形参须按 handler、event、data 排且不加 `*`
- 必填参数后紧跟同型可选参数提示用 `*` 隔开，防实参错位
- 注解被泛型包住的（`Awaitable[Message]`）属业务传参，不在本节口径
- 同步函数收 `Message` 属业务传参，不查事件名与注入位
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

from ._common import Finding

if TYPE_CHECKING:
    from ._common import FileData

_RAW_PARAM = "raw"

# 按名注入的上下文形参，名字即框架的取键
_CTX_PARAM = "ctx"
_CTX_TYPE = "HandlerContext"

# aiogram 全位置调用中间件的形参序列，名字与位置都算契约
_MIDDLEWARE_PARAMS = ("handler", "event", "data")
_MIDDLEWARE_SUFFIX = "Middleware"
_CALL_NAME = "__call__"

# 注入位判定的接收者，方法首参不算业务形参
_RECEIVERS: frozenset[str] = frozenset({"self", "cls"})

# aiogram 注入的原始事件类型名，含 types.Message 属性写法
_EVENT_TYPES: frozenset[str] = frozenset({"Message"})


def check(files: list[FileData]) -> list[Finding]:
    """扫描回调形参的注入命名与位置违规"""
    findings: list[Finding] = []
    for file in files:
        if file.parse_error:
            continue
        for node in ast.walk(file.tree):
            if isinstance(node, ast.ClassDef):
                findings.extend(_check_middleware(file, node))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                findings.extend(_check_swappable(file, node))
                if isinstance(node, ast.AsyncFunctionDef):
                    findings.extend(_check_injection(file, node))
    return findings


def _check_injection(file: FileData, node: ast.AsyncFunctionDef) -> list[Finding]:
    """协程逐形参判事件名、注入位与上下文名

    - 协程里出现带事件注解的形参才算框架绑定的回调，纯业务协程不套此口径
    """
    findings: list[Finding] = []
    params = _params(node)
    if not any(_is_event_arg(arg.annotation) for arg in params):
        return findings
    for index, arg in enumerate(params):
        if _is_event_arg(arg.annotation):
            if arg.arg != _RAW_PARAM:
                findings.append(
                    _f(
                        file,
                        arg.lineno,
                        f"协程 `{node.name}` 的注入形参 `{arg.arg}` 应改名 `{_RAW_PARAM}`",
                        True,
                    )
                )
            if index:
                findings.append(
                    _f(
                        file,
                        arg.lineno,
                        f"协程 `{node.name}` 的事件形参 `{arg.arg}` 须排首位",
                        True,
                    )
                )
        elif _is_ctx_arg(arg.annotation) and arg.arg != _CTX_PARAM:
            findings.append(
                _f(
                    file,
                    arg.lineno,
                    f"`{node.name}` 的上下文形参 `{arg.arg}` 应改名 `{_CTX_PARAM}`，改名即注入不到",
                    True,
                )
            )
    return findings


def _check_middleware(file: FileData, node: ast.ClassDef) -> list[Finding]:
    """中间件的 __call__ 形参序列与分隔符检查"""
    if not node.name.endswith(_MIDDLEWARE_SUFFIX):
        return []
    findings: list[Finding] = []
    for sub in node.body:
        if not isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if sub.name != _CALL_NAME:
            continue
        if sub.args.kwonlyargs:
            findings.append(
                _f(
                    file,
                    sub.lineno,
                    f"中间件 `{node.name}` 的 `{_CALL_NAME}` 由框架全位置调用，不许加 `*`",
                    True,
                )
            )
        names = tuple(arg.arg for arg in _params(sub))
        if names != _MIDDLEWARE_PARAMS:
            want = ", ".join(_MIDDLEWARE_PARAMS)
            findings.append(
                _f(
                    file,
                    sub.lineno,
                    f"中间件 `{node.name}` 的 `{_CALL_NAME}` 形参序列应为 `{want}`",
                    True,
                )
            )
    return findings


def _check_swappable(
    file: FileData, node: ast.FunctionDef | ast.AsyncFunctionDef
) -> list[Finding]:
    """必填首位可选紧邻同型时提示加 * 隔开"""
    params = _params(node)
    boundary = len(params) - len(node.args.defaults)
    if not 1 <= boundary < len(params) or node.args.vararg is not None:
        return []
    current, previous = params[boundary], params[boundary - 1]
    text = _type_text(file, current.annotation)
    if not text or text != _type_text(file, previous.annotation):
        return []
    return [
        _f(
            file,
            current.lineno,
            f"`{node.name}` 的 `{current.arg}` 与必填的 `{previous.arg}` 同为 `{text}`，加 `*` 隔开防错位",
            False,
        )
    ]


def _params(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[ast.arg]:
    """去掉接收者后的业务形参序列"""
    return [
        arg
        for arg in (*node.args.posonlyargs, *node.args.args)
        if arg.arg not in _RECEIVERS
    ]


def _is_event_arg(annotation: ast.expr | None) -> bool:
    """注解本体为 Message 或其可选写法即框架注入的原始事件，泛型包住的不算"""
    return _annotation_names(annotation) & _EVENT_TYPES != set()


def _is_ctx_arg(annotation: ast.expr | None) -> bool:
    """注解本体为 HandlerContext 即按名注入的上下文"""
    return _annotation_names(annotation) == {_CTX_TYPE}


def _annotation_names(annotation: ast.expr | None) -> set[str]:
    """取注解裸露的类型名，联合写法逐侧取，泛型内部不算"""
    if annotation is None:
        return set()
    if isinstance(annotation, ast.BinOp):
        return _annotation_names(annotation.left) | _annotation_names(annotation.right)
    if isinstance(annotation, ast.Name):
        return {annotation.id}
    if isinstance(annotation, ast.Attribute):
        return {annotation.attr}
    return set()


def _type_text(file: FileData, annotation: ast.expr | None) -> str:
    """注解源码文本，去空白与可选写法，供同型判定"""
    if annotation is None:
        return ""
    text = ast.get_source_segment(file.source, annotation) or ""
    return text.replace(" ", "").removesuffix("|None")


def _f(file: FileData, line: int, message: str, hard: bool) -> Finding:
    """生成一条回调形参违规"""
    return Finding("回调形参", file.rel, line, message, hard)
