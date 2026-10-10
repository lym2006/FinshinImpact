# devtools/_style_checks/_registry.py
"""检查登记表

- 具名收集九个分节的检查函数，赋予各自明确的消费者
- run_checks 统一入口，屏蔽命名节需要额外导入图的签名差异
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ._s1_skeleton import check as _check_skeleton
from ._s2_split import check as _check_split
from ._s3_docstring import check as _check_docstring
from ._s4_comment import check as _check_comment
from ._s5_naming import check as _check_naming
from ._s6_magic import check as _check_magic
from ._s7_text import check as _check_text
from ._s8_messages import check as _check_messages
from ._s9_typing import check as _check_typing

if TYPE_CHECKING:
    from ._common import FileData, Finding, ImportGraph

# 多数分节只读文件列表，命名与门面节额外需要跨模块导入图
_FILE_CHECKS = (
    _check_skeleton,
    _check_split,
    _check_docstring,
    _check_comment,
    _check_magic,
    _check_text,
    _check_messages,
    _check_typing,
)


def run_checks(files: list[FileData], graph: ImportGraph) -> list[Finding]:
    """按登记表顺序执行全部分节检查"""
    findings: list[Finding] = []
    for file_check in _FILE_CHECKS:
        findings.extend(file_check(files))
    findings.extend(_check_naming(files, graph))
    return findings
