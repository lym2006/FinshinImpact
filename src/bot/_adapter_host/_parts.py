# src/bot/_adapter_host/_parts.py
"""适配器入口装载

- 按清单定位入口模块，取到才导入
"""

from importlib import import_module

from core.domain import Platform
from exceptions import AdapterMissingError
from finshin_sdk import AdapterParts
from services.adapter_manifest import load_adapter_manifests


def parts_for(platform: Platform) -> AdapterParts:
    """按平台标识取适配器交出的四件

    - 清单缺席或字段非法即缺件
    - 入口模块在这一步才导入
    """
    manifest = load_adapter_manifests().get(platform)
    if manifest is None:
        raise AdapterMissingError(platform)

    return import_module(manifest.entry).parts()
