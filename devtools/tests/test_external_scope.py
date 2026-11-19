"""外部代码引用范围测试

- 覆盖随包树不查、干净的外部件放行、引了本体即报出引了谁与出处
- 覆盖标准库与相对导入不查
- 覆盖 tests 目录里的用例不参与装载即不查
- 覆盖界面库对两边都禁、平台框架只对插件禁
- 覆盖 Telegram 适配层这份现码伸向本体的手是一处不剩
- 覆盖体检扫的是空集时当场红，别让放行一切也算过
"""

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from adapter_presence import adapter_present  # noqa: E402

from exceptions import AdapterImportError, PluginImportError  # noqa: E402
from finshin_sdk.domain import PLUGINS_PKG, Platform  # noqa: E402
from services.adapter_manifest import load_adapter_manifests  # noqa: E402
from utils.external_scope import check_external_imports  # noqa: E402

_ADAPTER_LOADED = adapter_present()


def _adapter_package() -> str:
    """从清单表里取这一平台入口模块的顶层包名

    - 表里写谁就查谁，测试不自己记适配器的模块名
    """
    entry = load_adapter_manifests()[Platform.TELEGRAM].entry
    return entry.rpartition(".")[0]


class _TempPackage(unittest.TestCase):
    """在临时目录里落一只可导入的外部件"""

    def setUp(self) -> None:
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        root = Path(holder.name)
        sys.path.insert(0, str(root))
        self.addCleanup(sys.path.remove, str(root))
        self.root = root

    def _make(self, name: str, files: dict[str, str]) -> str:
        package = self.root / name
        package.mkdir()
        for file_name, body in files.items():
            target = package / file_name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body, encoding="utf-8")
        return name


class TestExternalImports(_TempPackage):
    """引用范围判据"""

    def test_bundled_root_is_not_checked(self) -> None:
        """随包树直接放过，目录不在盘上也不报错

        - 这条红了说明放行按恒启用表挑人，新加的随包件会被误拦
        """
        module = f"{PLUGINS_PKG}.inner"
        check_external_imports("inner", module, PluginImportError, PLUGINS_PKG)

    def test_clean_package_passes(self) -> None:
        """只引接口包与标准库的外部件放行"""
        name = self._make(
            "clean_tg",
            {
                "__init__.py": "import json\n\nfrom finshin_sdk import BaseAdapter\n",
                "entry.py": "from . import json as _json\n",
            },
        )
        check_external_imports("clean", name, AdapterImportError, "clean_root")

    def test_body_import_is_named(self) -> None:
        """引了本体内部即报出引了谁与落在哪份文件哪一行"""
        name = self._make(
            "sneaky_tg",
            {"__init__.py": "import json\n\nfrom utils import get_logger\n"},
        )
        with self.assertRaises(AdapterImportError) as ctx:
            check_external_imports("tg", name, AdapterImportError)
        self.assertEqual(ctx.exception.target, "utils")
        self.assertEqual(ctx.exception.where, "__init__.py:3")

    def test_import_inside_method_is_caught(self) -> None:
        """只在函数体里伸手本体一样报错

        - 这条红了说明扫描只看模块开头，延迟导入能绕过闸
        """
        name = self._make(
            "late_tg",
            {
                "__init__.py": "def _go() -> object:\n    import services\n    return services\n"
            },
        )
        with self.assertRaises(PluginImportError):
            check_external_imports("late", name, PluginImportError)

    def test_gui_library_is_forbidden_for_adapter(self) -> None:
        """适配器引界面库即报出引了谁"""
        name = self._make(
            "gui_tg",
            {"__init__.py": "from PySide6.QtWidgets import QWidget\n"},
        )
        with self.assertRaises(AdapterImportError) as ctx:
            check_external_imports("tg", name, AdapterImportError)
        self.assertEqual(ctx.exception.target, "PySide6.QtWidgets")

    def test_gui_library_is_forbidden_for_plugin(self) -> None:
        """插件引界面库同样报错，出处行号对得上

        - 这条红了说明界面库那条判据没跟着插件调用走
        """
        name = self._make(
            "gui_plugin",
            {"__init__.py": "import json\n\nfrom PySide6 import QtCore\n"},
        )
        with self.assertRaises(PluginImportError) as ctx:
            check_external_imports("gui", name, PluginImportError, PLUGINS_PKG)
        self.assertEqual(ctx.exception.where, "__init__.py:3")

    def test_platform_framework_is_forbidden_for_plugin_only(self) -> None:
        """平台框架适配器放行，插件报错

        - 这条红了说明平台框架的禁名跟着搭进了默认那一组
        """
        name = self._make(
            "aiogram_tg",
            {"__init__.py": "from aiogram import Router\n"},
        )
        check_external_imports("tg", name, AdapterImportError)
        with self.assertRaises(PluginImportError) as ctx:
            check_external_imports(
                "plug",
                name,
                PluginImportError,
                PLUGINS_PKG,
                extra_forbidden=("aiogram",),
            )
        self.assertEqual(ctx.exception.target, "aiogram")


class TestTestsDirIsSkipped(_TempPackage):
    """作者自己的用例不参与装载"""

    def test_body_import_inside_tests_dir_passes(self) -> None:
        """tests 目录里引本体不拦装载

        - 这条红了说明扫描把永远不会被 import 的文件也算进了引用范围
        """
        name = self._make(
            "tested_tg",
            {
                "__init__.py": "from finshin_sdk import BaseAdapter\n",
                "tests/test_unit.py": "from utils import get_logger\n",
            },
        )
        check_external_imports("tg", name, AdapterImportError)

    def test_body_import_outside_tests_dir_still_caught(self) -> None:
        """同一份件在 tests 之外伸手照旧报出"""
        name = self._make(
            "loose_tg",
            {
                "__init__.py": "from finshin_sdk import BaseAdapter\n",
                "helpers/scratch.py": "from utils import get_logger\n",
            },
        )
        with self.assertRaises(AdapterImportError) as ctx:
            check_external_imports("tg", name, AdapterImportError)
        self.assertEqual(ctx.exception.where, "helpers/scratch.py:1")


@unittest.skipUnless(_ADAPTER_LOADED, "适配层未装载，现码守卫跳过")
class TestTelegramAdapterStaysOutsideBody(unittest.TestCase):
    """现码守卫：Telegram 适配层不引本体任何一层

    - 这条红了说明适配层又伸回本体，拆出去的子仓当场不可信
    """

    def test_telegram_package_imports_no_body_root(self) -> None:
        check_external_imports("tg", _adapter_package(), AdapterImportError)

    def test_the_scan_walks_the_adapter_sources(self) -> None:
        """体检真扫得到适配器的源码

        - 定位到空目录时上一条会放行一切，全绿而瞎
        """
        package = _adapter_package()
        spec = importlib.util.find_spec(package)
        self.assertIsNotNone(spec, f"{package} 定位不到，体检扫的是空集")
        roots = list(spec.submodule_search_locations or [])
        self.assertTrue(roots, f"{package} 没有包根，装载侧的挂载写法变了")

        seen = [
            path
            for root in roots
            for path in Path(root).rglob("*.py")
            if "tests" not in path.relative_to(root).parts
        ]
        self.assertTrue(seen, "适配器源码一棵没扫到，这道守卫形同虚设")


if __name__ == "__main__":
    unittest.main()
