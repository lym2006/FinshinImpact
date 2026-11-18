"""文档写法分节 md 正文细则

- 正文行含全角或半角分号即报
- 相对 markdown 链接的目标文件不在场即报
- 围栏代码块行与行内代码段不算正文
- CHANGELOG.md 归日志与文案分节细则，本节不读
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from ._common import CHANGELOG_NAME, Finding

if TYPE_CHECKING:
    from ._common import FileData

# 一条一个事实，两件事拆成两条，两种分号同判
_SEMIS: tuple[str, ...] = ("；", ";")

# 反引号行内代码段，括起的是语法原样，不进判据
_INLINE_CODE_RE = re.compile(r"`[^`]*`")

# 围栏行，出现一次切换进出状态
_FENCE_RE = re.compile(r"^\s*```")

# markdown 行内链接，取目标段，目标含空白的不认
_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")

# 不查文件存在的目标前缀，外部地址与纯锚点归人工
_NON_FILE_PREFIXES: tuple[str, ...] = ("http://", "https://", "mailto:", "#")


def check(files: list[FileData]) -> list[Finding]:
    """扫描入库 md 正文的分号与相对链接存在性"""
    findings: list[Finding] = []
    for file in files:
        if file.path.suffix != ".md" or file.path.name == CHANGELOG_NAME:
            continue
        body = _body_lines(file.lines)
        findings.extend(_semicolon_findings(file, body))
        findings.extend(_link_findings(file, body))
    return findings


def _body_lines(lines: list[str]) -> list[tuple[int, str]]:
    """剔去围栏代码块行与行内代码段，行号与正文保持同形"""
    out: list[tuple[int, str]] = []
    in_fence = False
    for no, line in enumerate(lines, start=1):
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        out.append((no, _INLINE_CODE_RE.sub("", line)))
    return out


def _semicolon_findings(file: FileData, body: list[tuple[int, str]]) -> list[Finding]:
    """正文行出现任一分号即报，消息带行首截断"""
    findings: list[Finding] = []
    for no, text in body:
        if any(semicolon in text for semicolon in _SEMIS):
            shown = text.strip()[:30]
            findings.append(_f(file, no, f"正文行含分号：`{shown}…`"))
    return findings


def _link_findings(file: FileData, body: list[tuple[int, str]]) -> list[Finding]:
    """相对链接去掉锚点后解析，目标文件不在场即报"""
    findings: list[Finding] = []
    for no, text in body:
        for match in _LINK_RE.finditer(text):
            url = match.group(1)
            if url.startswith(_NON_FILE_PREFIXES):
                continue
            target = url.partition("#")[0]
            if not target:
                continue
            path = file.path.parent
            for part in target.split("/"):  # 逐级拼接，分隔符交给系统 Path 认
                path = path / part
            if not path.exists():
                findings.append(_f(file, no, f"相对链接目标不存在：`{url}`"))
    return findings


def _f(file: FileData, line: int, message: str) -> Finding:
    """构造本分节硬性违规条目"""
    return Finding("文档写法", file.rel, line, message, True)
