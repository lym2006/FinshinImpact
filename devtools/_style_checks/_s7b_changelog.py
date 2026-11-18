"""CHANGELOG 载体分节细则

- 行含全角分号即报
- 版本段标题按 `## [x.y.z] - YYYY-MM-DD` 判，放行 alpha、beta、rc 与 dev 后缀，`## [Unreleased]` 行不允许多余内容
- 子项行末要句号，止于冒号的纯主题行放行
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from ._common import CHANGELOG_NAME, Finding

if TYPE_CHECKING:
    from ._common import FileData

# 全角分号：一条一个事实，两件事拆成两条
_CN_SEMICOLON = "；"

# `## [` 起头的版本段标题行，方括号内容与行尾后缀分开取
_HEADING_RE = re.compile(r"^## \[([^\]]*)\](.*)$")

# 版本号主体：三段数字，预发布阶段取三档之一，dev 实录段只跟在阶段之后
_SEGMENT_RE = re.compile(r"^\d+\.\d+\.\d+(?:-(?:alpha|beta|rc)\.\d+(?:\.dev\d+)?)?$")

# 版本段标题的发布日期后缀
_DATE_SUFFIX_RE = re.compile(r"^ - \d{4}-\d{2}-\d{2}$")

# 列表子项行，含缩进子层
_BULLET_RE = re.compile(r"^\s*- \S")


def check_changelog(files: list[FileData]) -> list[Finding]:
    """扫描 CHANGELOG 的机器可判条目"""
    findings: list[Finding] = []
    for file in files:
        if file.path.name != CHANGELOG_NAME:
            continue
        for no, line in enumerate(file.lines, start=1):
            findings.extend(_line_findings(file, no, line))
    return findings


def _line_findings(file: FileData, no: int, line: str) -> list[Finding]:
    """单行过三类判据，同一行可叠报"""
    stripped = line.rstrip()
    findings: list[Finding] = []
    if _CN_SEMICOLON in line:
        shown = line.strip()[:30]
        findings.append(_f(file, no, f"行含全角分号：`{shown}…`"))
    heading = _HEADING_RE.match(stripped)
    if heading is not None:
        findings.extend(_heading_findings(file, no, stripped, heading))
    elif _BULLET_RE.match(line) and not stripped.endswith(("。", "：")):
        shown = stripped.strip()[:30]
        findings.append(_f(file, no, f"子项行末缺句号：`{shown}…`"))
    return findings


def _heading_findings(
    file: FileData, no: int, stripped: str, heading: re.Match[str]
) -> list[Finding]:
    """版本段标题行的版本号、日期后缀与 Unreleased 形状"""
    segment, suffix = heading.group(1), heading.group(2)
    shown = stripped[:40]
    if segment == "Unreleased":
        if suffix:
            return [
                _f(
                    file,
                    no,
                    f"版本段标题形状不符：`{shown}…`，Unreleased 行不允许多余内容",
                )
            ]
        return []
    if not _SEGMENT_RE.match(segment):
        return [
            _f(
                file,
                no,
                f"版本段标题形状不符：`[{segment}]`，应为 x.y.z 或 x.y.z-<阶段>.N[.devM]",
            )
        ]
    if not _DATE_SUFFIX_RE.match(suffix):
        return [
            _f(
                file,
                no,
                f"版本段标题形状不符：`{shown}…`，应为 `## [x.y.z] - YYYY-MM-DD`",
            )
        ]
    return []


def _f(file: FileData, line: int, message: str) -> Finding:
    """构造本分节硬性违规条目"""
    return Finding("日志与文案", file.rel, line, message, True)
