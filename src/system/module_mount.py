"""外部目录挂包

- 造包模块并把搜索位置指向目录
"""

import importlib.machinery
import importlib.util
import sys
from pathlib import Path


def mount_package(pkg: str, code_dir: Path) -> str:
    """把外部目录挂成指定包名

    - 包模块只登记搜索位置，不加载子模块
    - 包内相对引用走得通，跨出目录引不到随包私有件
    - 包名由调用方交出，不取目录名
    """
    if pkg not in sys.modules:
        spec = importlib.machinery.ModuleSpec(pkg, loader=None, is_package=True)
        spec.submodule_search_locations = [str(code_dir)]
        sys.modules[pkg] = importlib.util.module_from_spec(spec)
    return pkg


def mount_module(pkg: str, code_dir: Path) -> None:
    """把代码目录装成指定包名的模块

    - 目录名与包名不一致时按给定包名登记
    - 件内报错原样抛出，由装载侧记这只插件失败
    """
    init = code_dir / "__init__.py"
    spec = importlib.util.spec_from_file_location(
        pkg, init, submodule_search_locations=[str(code_dir)]
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"插件包 {pkg} 定位不到 {init}")
    sys.modules[pkg] = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sys.modules[pkg])
