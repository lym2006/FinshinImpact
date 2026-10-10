# devtools/_style_checks/_s5_naming.py
"""命名与门面导出分节检查

- 仅被自家包门面导入的子模块应带 `_` 前缀
- `_` 前缀模块被包外直接导入提示转正
- 被其他模块导入的符号禁 `_` 前缀，无任何消费者建议加
- 模块级常量细则委托 _s5c_constants
- 命名风格细则委托 _s5b_naming_style
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

from ._common import SECTIONS, Finding, ImportGraph, all_names
from ._s5b_naming_style import check_style
from ._s5c_constants import check_constants

if TYPE_CHECKING:
    from ._common import FileData


def check(files: list[FileData], graph: ImportGraph) -> list[Finding]:
    """扫描命名与门面导出违规"""
    findings: list[Finding] = []
    by_module = {f.module: f for f in files if f.module}
    dynamic = _getattr_names(files)
    findings.extend(_check_module_prefix(files, graph))
    findings.extend(_check_symbol_prefix(files, graph, by_module, dynamic))
    for file in files:
        if file.parse_error:
            continue
        findings.extend(check_constants(file, graph, dynamic))
    findings.extend(check_style(files))
    return findings


def _getattr_names(files: list[FileData]) -> set[str]:
    """全树内 getattr 第二参数字面量，动态加载消费方对静态图不可见"""
    names: set[str] = set()
    for file in files:
        if file.parse_error:
            continue
        for node in ast.walk(file.tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
                continue
            if node.func.id != "getattr" or len(node.args) < 2:
                continue
            second = node.args[1]
            if isinstance(second, ast.Constant) and isinstance(second.value, str):
                names.add(second.value)
    return names


def _outside_consumers(graph: ImportGraph, target: str) -> set[str]:
    """包外消费者集合"""
    package = target.rpartition(".")[0]
    consumers = graph.consumers.get(target, {})
    result: set[str] = set()
    for module in consumers:
        if module in {target, package}:
            continue
        if module.rpartition(".")[0] == package:
            continue
        if _is_test_module(module):
            continue
        if _is_ancestor_package(module, package):
            continue
        result.add(module)
    return result


def _is_test_module(module: str) -> bool:
    """测试模块白盒导入内部实现不构成转正依据"""
    parts = module.split(".")
    return any(p == "tests" or p.startswith("test_") for p in parts)


def _is_ancestor_package(module: str, package: str) -> bool:
    """子包模块使用父包内部模块属包内互用"""
    return bool(package) and module.startswith(f"{package}.")


def _check_module_prefix(files: list[FileData], graph: ImportGraph) -> list[Finding]:
    """子模块文件名的内外前缀规则"""
    findings: list[Finding] = []
    for file in files:
        if file.is_init or not file.module:
            continue
        consumers = graph.consumers.get(file.module, {})
        only_facade = bool(consumers) and set(consumers) == {file.package}
        if not file.stem.startswith("_") and only_facade:
            findings.append(
                _f(
                    file,
                    1,
                    f"子模块 `{file.rel}` 仅被包门面导入，按规范应加 `_` 前缀",
                    hard=False,
                ),
            )
        if file.stem.startswith("_"):
            outside = _outside_consumers(graph, file.module)
            if outside:
                joined = ", ".join(sorted(outside)[:3])
                findings.append(
                    _f(
                        file,
                        1,
                        f"内部模块 `{file.rel}` 被包外直接导入（{joined}），应转正去前缀",
                        hard=True,
                    ),
                )
    return findings


def _check_symbol_prefix(
    files: list[FileData],
    graph: ImportGraph,
    by_module: dict[str, FileData],
    dynamic: set[str],
) -> list[Finding]:
    """符号私有性一致检查"""
    findings: list[Finding] = []
    consumed: dict[str, dict[str, set[str]]] = {}
    for target, consumers in graph.consumers.items():
        merged: dict[str, set[str]] = {}
        for consumer, symbols in consumers.items():
            if consumer == target:
                continue
            if _is_test_module(consumer):
                continue
            for symbol in symbols:
                if symbol and symbol != "*":
                    merged.setdefault(symbol, set()).add(consumer)
        consumed[target] = merged
    for file in files:
        if file.parse_error or not file.module:
            continue
        defs = _def_defs(file)
        usage = consumed.get(file.module, {})
        exported = all_names(file)
        entry_names = _main_entry_names(file)
        for name, line in sorted(defs.items(), key=lambda kv: kv[1]):
            if name.startswith("__") or name == "__all__":
                continue
            if name in entry_names:
                continue
            users = usage.get(name, set())
            if name.startswith("_"):
                if users:
                    joined = ", ".join(sorted(users)[:3])
                    findings.append(
                        _f(
                            file,
                            line,
                            f"被其他模块导入的符号 `{name}` 带 `_` 前缀（{joined}）",
                            hard=True,
                        ),
                    )
            elif not users and name not in exported:
                if name in dynamic or _has_registration_decorator(file, name):
                    continue
                findings.append(
                    _f(
                        file,
                        line,
                        f"符号 `{name}` 无任何消费者且未进 __all__，应加 `_` 前缀",
                        hard=False,
                    ),
                )
    return findings


def _has_registration_decorator(file: FileData, name: str) -> bool:
    """定义带注册型装饰器时，装饰器即运行期消费方"""
    for node in file.tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if node.name != name:
            continue
        return any(
            isinstance(decorator, ast.Call) and bool(decorator.args)
            for decorator in node.decorator_list
        )
    return False


def _def_defs(file: FileData) -> dict[str, int]:
    """模块级函数与类名到行号"""
    return {
        node.name: node.lineno
        for node in file.tree.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
    }


def _main_entry_names(file: FileData) -> set[str]:
    """`if __name__ == "__main__"` 块内直接调用的函数名"""
    names: set[str] = set()
    for node in file.tree.body:
        if not (isinstance(node, ast.If) and _is_name_main(node.test)):
            continue
        for call in ast.walk(node):
            if isinstance(call, ast.Call) and isinstance(call.func, ast.Name):
                names.add(call.func.id)
    return names


def _is_name_main(test: ast.expr) -> bool:
    """判断 if 测试是否为 `__name__ == "__main__"`"""
    return (
        isinstance(test, ast.Compare)
        and isinstance(test.left, ast.Name)
        and test.left.id == "__name__"
    )


def _f(file: FileData, line: int, message: str, hard: bool) -> Finding:
    """构造本分节违规条目"""
    return Finding(SECTIONS[4], file.rel, line, message, hard)
