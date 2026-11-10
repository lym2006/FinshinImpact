# src/finshin_sdk/dto/_adapter.py
"""适配器数据传输对象

- 定义外部适配器自描述清单
- 字段与 adapter.toml 对应
"""

from dataclasses import dataclass

from ..domain import Platform


@dataclass(frozen=True, slots=True)
class AdapterManifestDTO:
    """外部适配器自描述清单

    - 入口模块导入路径按目录名拼出
    - 接口包版本下限取自清单，没写即不设限
    """

    platform: Platform
    deps: tuple[str, ...]
    requires_sdk: str
    entry: str
