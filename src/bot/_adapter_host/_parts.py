# src/bot/_adapter_host/_parts.py
"""适配器入口装载

- 按清单定位入口模块，取到才导入
"""

from importlib import import_module

from packaging.version import InvalidVersion, Version

from exceptions import AdapterMissingError, AdapterOutOfDateError
from finshin_sdk import SDK_VERSION, AdapterParts
from finshin_sdk.domain import Platform
from services.adapter_manifest import load_adapter_manifests


def parts_for(platform: Platform) -> AdapterParts:
    """按平台标识取适配器交出的四件

    - 清单缺席或字段非法即缺件
    - 清单要的接口版本比本机新即拒载，拒在导入入口之前
    """
    manifest = load_adapter_manifests().get(platform)
    if manifest is None:
        raise AdapterMissingError(platform)
    if not _sdk_is_enough(manifest.requires_sdk):
        raise AdapterOutOfDateError(platform, manifest.requires_sdk, SDK_VERSION)

    return import_module(manifest.entry).parts()


def _sdk_is_enough(requires: str) -> bool:
    """判定本机接口包够不够清单要的版本

    - 没写这一行即不设限
    - 版本串读不懂当不够，拒载那句把原串递给用户
    """
    if not requires:
        return True
    try:
        return Version(SDK_VERSION) >= Version(requires)
    except InvalidVersion:
        return False
