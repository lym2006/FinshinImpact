# src/finshin_sdk/domain/_adapter.py
"""外部适配器词表

- 定义适配器树包名、清单文件名、入口模块名、清单键名与字段规格
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

# 适配器树顶层包名，find_spec 与动态导入路径共用同值
ADAPTERS_PKG = "adapters"

# 清单文件名，位于各适配器目录
ADAPTER_MANIFEST_FILE = "adapter.toml"

# 入口模块名由本体规定，清单不写这一行
ADAPTER_ENTRY_MODULE = "entry"


class AdapterManifestKey(StrEnum):
    """适配器清单键名"""

    PLATFORM = "platform"
    DEPS = "deps"
    REQUIRES_SDK = "requires_sdk"


@dataclass(frozen=True, slots=True)
class AdapterFieldSpec:
    """适配器清单字段规格"""

    key: AdapterManifestKey
    value_type: type
    default: Any
    required: bool = False


ADAPTER_MANIFEST_FIELDS: tuple[AdapterFieldSpec, ...] = (
    AdapterFieldSpec(AdapterManifestKey.PLATFORM, str, "", required=True),
    AdapterFieldSpec(AdapterManifestKey.DEPS, list, ()),
    AdapterFieldSpec(AdapterManifestKey.REQUIRES_SDK, str, ""),
)
