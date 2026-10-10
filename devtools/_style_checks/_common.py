# devtools/_style_checks/_common.py
"""编码规范检查公共设施

- 文件装载、点分模块名解析与解析失败记录
- 跨模块导入图构建，供命名与门面分节使用
- 违规条目数据结构与整行注释提取
"""

from __future__ import annotations

import ast
import io
import re
import tokenize
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

# 扫描器基础配置
SECTIONS: tuple[str, ...] = (
    "文件骨架",
    "拆分粒度",
    "Docstring",
    "注释",
    "命名与门面导出",
    "魔法数字与字符串",
    "日志与文案",
    "文案类",
    "类型注解",
)

_EXCLUDE_DIRS: frozenset[str] = frozenset(
    {
        "__pycache__",
        ".venv",
        ".git",
        ".pytest_cache",
        ".ruff_cache",
        "build",
        "dist",
        "node_modules",
        "tests",
    }
)
_EXCLUDE_SUFFIXES: tuple[str, ...] = (".egg-info",)

_CJK_RE = re.compile(r"[\u4e00-\u9fff]")


@dataclass(frozen=True)
class Finding:
    """规范违规条目"""

    section: str
    rel: str
    line: int
    message: str
    hard: bool


@dataclass
class FileData:
    """单文件的检查上下文"""

    path: Path
    rel: str
    module: str
    source: str
    lines: list[str]
    tree: ast.Module
    comments: dict[int, str] = field(default_factory=dict)
    eol: dict[int, str] = field(default_factory=dict)
    parse_error: str = ""

    @property
    def is_init(self) -> bool:
        """是否为包门面文件"""
        return self.path.name == "__init__.py"

    @property
    def package(self) -> str:
        """所在包的点分名"""
        return self.module if self.is_init else self.module.rpartition(".")[0]

    @property
    def stem(self) -> str:
        """去扩展名的文件名"""
        return self.path.stem


def has_cjk(text: str) -> bool:
    """判断字符串是否含中文字符"""
    return bool(_CJK_RE.search(text))


def all_names(file: FileData) -> set[str]:
    """__all__ 中列出的符号"""
    for node in file.tree.body:
        # 先排除非赋值语句，窄化才能延续到取 node.value 处
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        names: list[ast.expr] = (
            list(node.targets) if isinstance(node, ast.Assign) else [node.target]
        )
        if any(isinstance(t, ast.Name) and t.id == "__all__" for t in names):
            value = node.value
            if isinstance(value, (ast.List, ast.Tuple, ast.Set)):
                return {
                    e.value
                    for e in value.elts
                    if isinstance(e, ast.Constant) and isinstance(e.value, str)
                }
    return set()


def load_files(root: Path, targets: list[Path]) -> list[FileData]:
    """装载扫描范围内的全部 py 文件"""
    files: list[FileData] = []
    for target in targets:
        for path in _iter_py(target):
            rel = path.relative_to(root).as_posix()
            files.append(_read_file(path, rel, root))
    return sorted(files, key=lambda f: f.rel)


def _iter_py(target: Path) -> Iterator[Path]:
    """遍历目标下的 py 文件并跳过缓存目录"""
    if target.is_file() and target.suffix == ".py":
        yield target
        return
    for path in target.rglob("*.py"):
        parts = path.relative_to(target).parts[:-1]
        if any(p in _EXCLUDE_DIRS or p.endswith(_EXCLUDE_SUFFIXES) for p in parts):
            continue
        yield path


def _read_file(path: Path, rel: str, root: Path) -> FileData:
    """读文件并解析 ast，解析失败只记录不中断"""
    source = path.read_text(encoding="utf-8-sig", errors="replace")
    module = _module_name(path, root)
    try:
        tree = ast.parse(source, filename=str(path))
        error = ""
    except SyntaxError as exc:
        tree = ast.Module(body=[], type_ignores=[])
        error = f"{exc.lineno or 1}: {exc.msg}"
    comments, eol = _extract_comments(source)
    return FileData(
        path=path,
        rel=rel,
        module=module,
        source=source,
        lines=source.splitlines(),
        tree=tree,
        comments=comments,
        eol=eol,
        parse_error=error,
    )


def _module_name(path: Path, root: Path) -> str:
    """沿 __init__.py 链上溯解析点分模块名"""
    if path.name == "__init__.py":
        parts: list[str] = []
        cur = path.parent
    else:
        parts = [path.stem]
        cur = path.parent
    while (cur / "__init__.py").is_file() and cur != root:
        parts.append(cur.name)
        cur = cur.parent
    module = ".".join(reversed(parts))
    if module.startswith("src."):
        module = module[4:]
    return module


def _extract_comments(source: str) -> tuple[dict[int, str], dict[int, str]]:
    """提取整行注释与行尾注释，行号到去掉井号的正文"""
    full: dict[int, str] = {}
    eol: dict[int, str] = {}
    lines = source.splitlines()
    try:
        tokens = tokenize.generate_tokens(io.StringIO(source).readline)
        for tok in tokens:
            if tok.type != tokenize.COMMENT:
                continue
            text = tok.string.lstrip("#").strip()
            if lines[tok.start[0] - 1][: tok.start[1]].strip():
                eol[tok.start[0]] = text
            else:
                full[tok.start[0]] = text
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return full, eol
    return full, eol


class ImportGraph:
    """跨模块导入关系图

    - 记录每个模块被谁导入、导入了哪些符号
    - 相对导入按所在包逐级解析
    """

    def __init__(self, files: list[FileData]) -> None:
        """从文件列表构建导入图"""
        self.modules: set[str] = {f.module for f in files if f.module}
        self.consumers: dict[str, dict[str, set[str]]] = {}
        self.importers_of: dict[str, set[str]] = {}
        self.edges: list[tuple[str, str, int]] = []
        for file in files:
            if file.parse_error:
                continue
            self._walk(file)

    def _walk(self, file: FileData) -> None:
        """登记单文件内全部导入语句与模块属性访问"""
        bindings: dict[str, str] = {}
        for node in ast.walk(file.tree):
            if isinstance(node, ast.Import):
                self._plain_import(file, node, bindings)
            elif isinstance(node, ast.ImportFrom):
                self._from_import(file, node, bindings)
        self._attr_uses(file, bindings)

    def _plain_import(
        self, file: FileData, node: ast.Import, bindings: dict[str, str]
    ) -> None:
        """处理 import a.b 形式，登记本地别名到模块"""
        for alias in node.names:
            local = alias.asname or alias.name.split(".")[0]
            bindings[local] = alias.name
            self._consume(file, alias.name, "", node.lineno)

    def _from_import(
        self, file: FileData, node: ast.ImportFrom, bindings: dict[str, str]
    ) -> None:
        """处理 from x import y 形式并解析相对层级"""
        if node.level:
            base = self._resolve_base(file, node)
            if base is None:
                return
            target = f"{base}.{node.module}" if node.module else base
        else:
            if not node.module:
                return
            target = node.module
        for alias in node.names:
            name = alias.name
            if self._is_submodule(target, name):
                local = alias.asname or name
                bindings[local] = f"{target}.{name}"
                self._consume(file, f"{target}.{name}", "", node.lineno)
                continue
            self._consume(file, target, name, node.lineno)

    def _attr_uses(self, file: FileData, bindings: dict[str, str]) -> None:
        """登记 别名.属性 形式对导入模块成员的消费"""
        if not bindings:
            return
        for node in ast.walk(file.tree):
            if not isinstance(node, ast.Attribute):
                continue
            value = node.value
            if isinstance(value, ast.Name) and value.id in bindings:
                self._consume(file, bindings[value.id], node.attr, node.lineno)

    def _is_submodule(self, package: str, name: str) -> bool:
        """判断 from pkg import name 的 name 是否子模块"""
        full = f"{package}.{name}" if package else name
        return full in self.modules

    def _resolve_base(self, file: FileData, node: ast.ImportFrom) -> str | None:
        """把相对导入折算成绝对包名"""
        if not node.level:
            return node.module or ""
        parts = file.module.split(".") if file.module else []
        package_parts = parts if file.is_init else parts[:-1]
        up = node.level - 1
        if up > len(package_parts):
            return None
        head = package_parts[: len(package_parts) - up] if up else package_parts
        return ".".join(head)

    def _consume(self, file: FileData, target: str, symbol: str, lineno: int) -> None:
        """记录 target 被 file 消费"""
        if not target or target == file.module:
            return
        bucket = self.consumers.setdefault(target, {})
        bucket.setdefault(file.module, set()).add(symbol)
        self.importers_of.setdefault(target, set()).add(file.module)
        self.edges.append((file.module, target, lineno))
