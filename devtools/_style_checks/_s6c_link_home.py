"""链接归家细则

- 在线地址与协议头字面量只许写在地址的家那几份文件里
- 家清单按路径片段写死，新增家要同时改这份清单
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

from ._common import Finding

if TYPE_CHECKING:
    from ._common import FileData

# 地址的家：本体一份、启动器两份、构建原料清单一份、配置默认值与文案示例各一处
# 扫描器自己的判据串与用例夹具里的假地址同属合法写法
_LINK_HOMES: tuple[str, ...] = (
    "system/links.py",
    "pack_spec.py",
    "pack_fetch.py",
    "AI/config.py",
    "skin/messages",
    "_style_checks",
    "tests",
)

_SCHEMES: tuple[str, ...] = ("http://", "https://")


def check_links(files: list[FileData]) -> list[Finding]:
    """点名写在家之外的在线地址"""
    findings: list[Finding] = []
    for file in files:
        if file.parse_error or _is_home(file.rel):
            continue
        for node in ast.walk(file.tree):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            if not any(scheme in node.value for scheme in _SCHEMES):
                continue
            findings.append(
                Finding(
                    "魔法数字与字符串",
                    file.rel,
                    node.lineno,
                    f"在线地址裸写在家外，只许写在家清单里：{node.value[:32]}",
                    True,
                )
            )
    return findings


def _is_home(rel: str) -> bool:
    """判这份文件是不是地址的家"""
    return any(part in rel.replace("\\", "/") for part in _LINK_HOMES)
