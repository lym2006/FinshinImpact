# devtools/_style_checks/_waivers.py
"""待核豁免清单

- 读取清单文件，按分节、路径与消息子串罩住已审过的待核条目
- 条目本轮没罩住任何违规即判失效，回吐给调用方报出
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from ._common import Finding

_SPLIT_SECTION = "拆分粒度"
_FILE_SIZE_PREFIX = "单文件"


@dataclass(frozen=True)
class Waiver:
    """一条已登记的待核豁免"""

    section: str
    path: str
    reason: str
    match: str = ""

    def covers(self, finding: Finding) -> bool:
        """判定本条是否罩住这条违规，不看行号防漂移

        - 硬性违规一律不罩，清单只用于已审的待核
        - 单文件行数超限也不罩，它只认拆或抬常量
        """
        return (
            not finding.hard
            and not _file_size_finding(finding)
            and self.section == finding.section
            and self.path == finding.rel
            and (not self.match or self.match in finding.message)
        )


def _file_size_finding(finding: Finding) -> bool:
    """单文件行数超限的待核不参与豁免

    - 罩住等于给那个文件永久关掉阈值，越该拆越没声
    """
    return finding.section == _SPLIT_SECTION and finding.message.startswith(
        _FILE_SIZE_PREFIX
    )


def load_waivers(path: Path) -> tuple[Waiver, ...]:
    """读取豁免清单，文件不存在即空清单

    - 缺 section、path、reason 任一键即报错，不静默跳过半条豁免
    """
    if not path.exists():
        return ()
    with path.open("rb") as handle:
        raw = tomllib.load(handle)
    return tuple(
        Waiver(
            section=item["section"],
            path=item["path"],
            reason=item["reason"],
            match=item.get("match", ""),
        )
        for item in raw.get("waiver", ())
    )


def apply_waivers(
    findings: list[Finding], waivers: tuple[Waiver, ...]
) -> tuple[list[Finding], tuple[Waiver, ...]]:
    """剔除已豁免条目，并回吐一条都没命中的失效豁免"""
    kept: list[Finding] = []
    alive: set[int] = set()
    for finding in findings:
        for index, waiver in enumerate(waivers):
            if waiver.covers(finding):
                alive.add(index)
                break
        else:
            kept.append(finding)
    dead = tuple(w for i, w in enumerate(waivers) if i not in alive)
    return kept, dead
