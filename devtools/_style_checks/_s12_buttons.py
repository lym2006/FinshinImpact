"""按钮样式分节检查

- 按钮规则只许写在 qss 目录的 _buttons.py
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from ._common import Finding

if TYPE_CHECKING:
    from ._common import FileData

_SECTION = "按钮样式"
_QSS_DIR = "src/skin/qss/"
_BUTTON_FILE = "src/skin/qss/_buttons.py"

_SELECTOR_RE = re.compile(r"\bQPushButton\b")


def check(files: list[FileData]) -> list[Finding]:
    """扫描 qss 目录里越界的按钮规则"""
    findings: list[Finding] = []
    for file in files:
        if not _is_window_qss(file.rel):
            continue
        for number, line in enumerate(file.lines, start=1):
            if _SELECTOR_RE.search(line):
                findings.append(
                    _f(file, number, "按钮规则越界，应移进 _buttons.py 复用")
                )
    return findings


def _is_window_qss(rel: str) -> bool:
    """是否该窗样式文件自写按钮规则"""
    if not rel.startswith(_QSS_DIR):
        return False
    return rel != _BUTTON_FILE


def _f(file: FileData, line: int, message: str) -> Finding:
    """构造本分节违规条目"""
    return Finding(_SECTION, file.rel, line, message, True)
