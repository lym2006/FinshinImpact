"""外部代码的引用范围检查

- 导入之前先扫一遍源码，本体各层一律不许引
- 插件与适配器共用这一份判据，该报哪只异常由调用方交来
"""

import ast
import importlib.util
from collections.abc import Callable
from pathlib import Path

# 作者放在 tests 目录里的用例不参与装载，这一道不查它
_TEST_DIR = "tests"

# 外部代码不许伸进去的顶层包名，接口包与标准库不在其中
_BODY_ROOTS = frozenset(
    {
        "finshin",
        "bootstrap",
        "bot",
        "bundled",
        "core",
        "data",
        "exceptions",
        "services",
        "skin",
        "system",
        "ui",
        "utils",
    }
)


def check_external_imports(
    source: str,
    module: str,
    make_error: Callable[[str, str, str], Exception],
    bundled_root: str | None = None,
) -> None:
    """扫这份件的源码，引了本体内部即按交来的错法报错

    - 顶层包名撞上 bundled_root 即随包树，不查
    - 没给 bundled_root 即这一族没有随包那一份，一律照查
    - 只定位目录不执行，定位不到即放过，缺件那步自有另一句报
    """
    if bundled_root is not None and module.partition(".")[0] == bundled_root:
        return
    offence = _first_body_import(module)
    if offence is not None:
        raise make_error(source, offence[0], offence[1])


def _first_body_import(module: str) -> tuple[str, str] | None:
    """取这份件里第一处伸向本体的导入，交出「引了谁」与出处

    - 只数会被装载的源码，作者放在 tests 目录里的用例不参与
    """
    spec = importlib.util.find_spec(module)
    if spec is None:
        return None
    dirs = list(spec.submodule_search_locations or [])
    if not dirs and spec.origin:
        dirs = [str(Path(spec.origin).parent)]
    for root in dirs:
        for path in sorted(Path(root).rglob("*.py")):
            label = path.relative_to(root)
            if _TEST_DIR in label.parts:
                continue
            offence = _file_body_import(path, label)
            if offence is not None:
                return offence
    return None


def _file_body_import(file: Path, label: Path) -> tuple[str, str] | None:
    """取这份文件里第一处伸向本体的导入

    - 交出「引了谁」与「落在哪份文件哪一行」
    - 出处按件的根目录写相对路径，子目录里的那份才找得着
    - 文件读不出或语法不通即跳过，导入那步自有交代
    """
    try:
        tree = ast.parse(file.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return None
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        for name in _imported_names(node):
            if name.partition(".")[0] in _BODY_ROOTS:
                return name, f"{label.as_posix()}:{node.lineno}"
    return None


def _imported_names(node: ast.Import | ast.ImportFrom) -> tuple[str, ...]:
    """一条导入语句交出的绝对名，相对导入没有"""
    if isinstance(node, ast.ImportFrom):
        return () if node.level or not node.module else (node.module,)
    if isinstance(node, ast.Import):
        return tuple(alias.name for alias in node.names)
    return ()
