# src/core/dto/_adapter.py
"""适配器数据传输对象

- 定义外部适配器自描述清单
- 字段与 adapter.toml 对应
"""

from dataclasses import dataclass

from ..domain import Platform


@dataclass(frozen=True, slots=True)
class AdapterManifestDTO:
    """外部适配器自描述清单

    - entry 是按目录名拼出的入口模块导入路径
    """

    platform: Platform
    version: str
    deps: tuple[str, ...]
    entry: str
