"""主仓用例树归属检查

- 顶层用例不在模块开头引装载根，模块级引用是拆仓当天跑不起来的债
- 函数体内引适配器只许配着装载在场判定，缺判定即裸依赖
- 本体与打包侧静态不引适配器，取件只走清单里那个模块名
- 整棵适配器专属树按目录名认，不靠清单
"""

import ast
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

_ROOT = Path(__file__).resolve().parents[2]
_TESTS = _ROOT / "devtools" / "tests"
# 装载根目录名与已装适配器包名，两样都算伸进适配层
_ADAPTER_PREFIXES = ("finshin/adapter", "finshin_adapter_")
_GATE_MARKER = "adapter_present()"

# 本体侧两棵树，静态引适配器就是假护栏，一律禁
_BODY_STEMS = ("src", "packaging")


def _module_imports(tree: ast.Module) -> list[str]:
    """取模块开头的导入模块名"""
    names: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.append(node.module)
    return names


def _nested_imports(tree: ast.Module) -> list[str]:
    """取函数体内部的导入模块名"""
    module_level = {id(node) for node in tree.body}
    names: list[str] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, (ast.Import, ast.ImportFrom))
            and id(node) not in module_level
        ):
            if isinstance(node, ast.Import):
                names.extend(alias.name for alias in node.names)
            elif node.module:
                names.append(node.module)
    return names


class TestNoTopLevelAdapterImport(unittest.TestCase):
    """顶层用例的模块开头不引装载根"""

    def test_body_start_is_clean(self) -> None:
        files = sorted(_TESTS.glob("*.py"))
        self.assertTrue(files, "没找到用例文件，扫描根写错了")
        for path in files:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for name in _module_imports(tree):
                with self.subTest(file=path.name, imported=name):
                    self.assertFalse(
                        name.startswith(_ADAPTER_PREFIXES),
                        f"{path.name} 在模块开头引了装载根，拆仓后这条 import 就断了",
                    )


class TestNestedAdapterImportIsGated(unittest.TestCase):
    """函数体内引适配器要带在场判定"""

    def test_lazy_import_carries_gate(self) -> None:
        for path in sorted(_TESTS.glob("*.py")):
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
            hits = [
                name
                for name in _nested_imports(tree)
                if name.startswith(_ADAPTER_PREFIXES)
            ]
            if not hits:
                continue
            with self.subTest(file=path.name):
                self.assertIn(
                    _GATE_MARKER,
                    source,
                    "缺装载在场判定，没挂载时会报错而不是跳过",
                )


class TestBodyNeverImportsAdapter(unittest.TestCase):
    """本体与打包侧静态不引适配器"""

    def test_no_static_adapter_import(self) -> None:
        offenders: list[str] = []
        for stem in _BODY_STEMS:
            files = sorted((_ROOT / stem).rglob("*.py"))
            self.assertTrue(files, f"{stem} 一棵没扫到，扫描根写错了")
            for path in files:
                tree = ast.parse(path.read_text(encoding="utf-8"))
                for name in _module_imports(tree) + _nested_imports(tree):
                    if name.startswith(_ADAPTER_PREFIXES):
                        offenders.append(f"{path.relative_to(_ROOT)} 引了 {name}")
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
