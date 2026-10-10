# devtools/_style_checks/__init__.py
"""编码规范静态检查包

- 非空门面代发入口脚本所需符号
- 子模块均为内部实现，消费方一律经本门面直连
"""

from ._common import SECTIONS, Finding, ImportGraph, load_files
from ._registry import run_checks

__all__ = [
    # 公共设施
    "SECTIONS",
    "Finding",
    "ImportGraph",
    "load_files",
    # 统一入口
    "run_checks",
]
