# devtools/_style_checks/_s1_skeleton.py
"""文件骨架分节检查

- 首行相对路径注释与文件名一致
- 模块 docstring 存在且首行为定位
- 禁止区块标题注释与装饰横线
- __all__ 只属于非空包门面，且多项成员须按含义分组
- 主入口 if __name__ 块位于文件末尾
"""

from __future__ import annotations

import ast
import re
from typing import TYPE_CHECKING

from ._common import SECTIONS, Finding

if TYPE_CHECKING:
    from ._common import FileData

# 骨架废话标题词表
_SECTION_WORDS = (
    "导入",
    "全局常量",
    "常量与配置",
    "对外暴露",
    "核心业务",
    "业务逻辑",
    "主程序入口",
    "脚本直接运行",
    "主入口",
)

# 装饰横线
_DECORATION_RE = re.compile(r"[=\-*~─—_]{4,}")

# __all__ 成员达此数即须按含义分组，单项豁免分组注释
_GROUP_MIN = 2


def check(files: list[FileData]) -> list[Finding]:
    """扫描文件骨架违规"""
    findings: list[Finding] = []
    for file in files:
        if file.parse_error:
            findings.append(
                _f(file, 1, f"解析失败无法检查骨架：{file.parse_error}", hard=True),
            )
            continue
        findings.extend(_check_first_line(file))
        findings.extend(_check_module_docstring(file))
        findings.extend(_check_section_titles(file))
        findings.extend(_check_dunder_all(file))
        findings.extend(_check_main_entry(file))
    return findings


def _check_first_line(file: FileData) -> list[Finding]:
    """首行路径注释检查"""
    first = file.lines[0].strip() if file.lines else ""
    if not first.startswith("#"):
        return [_f(file, 1, "首行缺少相对路径注释", hard=False)]
    claimed = first.lstrip("#").strip()
    if claimed != file.rel:
        return [
            _f(
                file,
                1,
                f"首行路径注释 `{claimed}` 与实际 `{file.rel}` 不一致",
                hard=True,
            )
        ]
    return []


def _check_module_docstring(file: FileData) -> list[Finding]:
    """模块 docstring 检查"""
    node = _module_docstring_node(file)
    if node is None:
        return [_f(file, 1, "缺少模块 docstring", hard=False)]
    findings: list[Finding] = []
    seen_detail = False
    for line in range(node.lineno + 1, (node.end_lineno or node.lineno) + 1):
        raw = file.lines[line - 1].strip().strip('"').strip("'").strip()
        if not raw or raw in ('"""', "'''"):
            continue
        if not seen_detail:
            seen_detail = True
        if not raw.startswith("-"):
            findings.append(
                _f(file, line, f"模块 docstring 详情行未以 `-` 起头：{raw}", hard=False)
            )
    return findings


def _module_docstring_node(file: FileData) -> ast.Constant | None:
    """取模块 docstring 字面量节点"""
    if not file.tree.body:
        return None
    first = file.tree.body[0]
    if (
        isinstance(first, ast.Expr)
        and isinstance(first.value, ast.Constant)
        and isinstance(first.value.value, str)
    ):
        return first.value
    return None


def _check_section_titles(file: FileData) -> list[Finding]:
    """区块标题注释与装饰横线"""
    findings: list[Finding] = []
    for line, text in sorted(file.comments.items()):
        if _DECORATION_RE.match(text):
            findings.append(
                _f(file, line, f"装饰横线/区块标题注释：`# {text}`", hard=True)
            )
            continue
        core = re.sub(r"[=\-─—#\s]+", "", text)
        if core in _SECTION_WORDS:
            findings.append(_f(file, line, f"区块标题注释：`# {text}`", hard=True))
    return findings


def _check_dunder_all(file: FileData) -> list[Finding]:
    """__all__ 归属与分组检查"""
    node = _all_node(file)
    line = node.lineno if node else 1
    if not file.is_init:
        if node is None:
            return []
        return [_f(file, line, "业务模块不应写 __all__，调用方直连导入", hard=True)]
    if not _has_import(file):
        if node is None:
            return []
        return [_f(file, line, "门面文件无代发符号却写 __all__", hard=False)]
    if node is None:
        return [_f(file, 1, "非空门面缺 __all__，代发符号无对外清单", hard=True)]
    members = _all_members(node)
    if len(members) < _GROUP_MIN:
        return []

    # 组名注释只可能落在 __all__ 赋值自身的行区间内
    span = range(node.lineno, (node.end_lineno or node.lineno) + 1)
    if any(i in file.comments for i in span):
        return []
    return [
        _f(
            file,
            node.lineno,
            f"__all__ 有 {len(members)} 项却无分组注释，应按含义补 `# 组名`",
            hard=True,
        )
    ]


def _has_import(file: FileData) -> bool:
    """模块顶层是否含导入语句"""
    return any(
        isinstance(node, (ast.Import, ast.ImportFrom)) for node in file.tree.body
    )


def _all_node(file: FileData) -> ast.Assign | ast.AnnAssign | None:
    """模块顶层 __all__ 赋值节点"""
    for node in file.tree.body:
        # 先排除非赋值语句，窄化才能延续到 return 处
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        names: list[ast.expr] = (
            list(node.targets) if isinstance(node, ast.Assign) else [node.target]
        )
        if any(isinstance(t, ast.Name) and t.id == "__all__" for t in names):
            return node
    return None


def _all_members(node: ast.Assign | ast.AnnAssign) -> list[str]:
    """__all__ 列出的成员名，非字面量容器按零项处理"""
    value = node.value
    if not isinstance(value, (ast.List, ast.Tuple, ast.Set)):
        return []
    return [
        e.value
        for e in value.elts
        if isinstance(e, ast.Constant) and isinstance(e.value, str)
    ]


def _check_main_entry(file: FileData) -> list[Finding]:
    """If __name__ 主入口必须在文件最底部"""
    main_nodes = [
        node
        for node in file.tree.body
        if isinstance(node, ast.If) and _is_name_main(node.test)
    ]
    if not main_nodes:
        return []
    last = main_nodes[-1]
    tail = last.end_lineno or last.lineno
    after = [n for n in file.tree.body if n.lineno > tail]
    if after:
        return [
            _f(
                file,
                after[0].lineno,
                f"主入口之后仍有代码（第 {after[0].lineno} 行 {type(after[0]).__name__}）",
                hard=False,
            ),
        ]
    return []


def _is_name_main(test: ast.expr) -> bool:
    """判断 if 测试是否为 __name__ == '__main__'"""
    return (
        isinstance(test, ast.Compare)
        and isinstance(test.left, ast.Name)
        and test.left.id == "__name__"
    )


def _f(file: FileData, line: int, message: str, hard: bool) -> Finding:
    """构造本分节违规条目"""
    return Finding(SECTIONS[0], file.rel, line, message, hard)
