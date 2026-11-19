"""适配器入口装载

- 按清单定位入口模块，外部件先查引用范围再导入
- 取到件后把它的来源路径落到调试日志
"""

from importlib import import_module

from exceptions import (
    AdapterImportError,
    AdapterMissingError,
    AdapterNotInstalledError,
    AdapterOutOfDateError,
)
from finshin_sdk import SDK_VERSION, AdapterParts
from finshin_sdk.domain import Platform
from services.adapter_manifest import load_adapter_manifests
from system.versions import requires_met
from utils import get_logger
from utils.external_scope import check_external_imports

_logger = get_logger("Mgr.Adapter")


def parts_for(platform: Platform) -> AdapterParts:
    """按平台标识取适配器交出的入口件

    - 清单缺席或字段非法即缺件
    - 本机接口包不在清单要求的区间内即拒载，拒在导入入口之前
    - 声明在场而环境里取不到那只包，即按没装进环境交代
    - 随包树之外的适配器引了本体内部即拒载，同样拒在导入之前
    """
    manifest = load_adapter_manifests().get(platform)
    if manifest is None:
        raise AdapterMissingError(platform)
    if not _sdk_in_range(manifest.requires_sdk):
        raise AdapterOutOfDateError(platform, manifest.requires_sdk, SDK_VERSION)

    package = manifest.entry.rpartition(".")[0]
    check_external_imports(str(platform), package, AdapterImportError)
    try:
        entry = import_module(manifest.entry)
    except ModuleNotFoundError as exc:
        raise AdapterNotInstalledError(platform, str(exc.name or "")) from exc
    _logger.debug(f"{platform} 适配器来自 {entry.__file__}")
    return entry.parts()


def _sdk_in_range(requires: str) -> bool:
    """判定本机接口包是否在清单要求的区间内

    - 没写这一行即不设限
    - 版本串读不懂按不满足处理，拒载那句把原串递给用户
    """
    if not requires:
        return True
    return requires_met(SDK_VERSION, requires) is True
