# devtools/check_coding_style.py
r"""编码规范扫描器

- 按 docs/coding-style.md 九个分节静态检查代码
- 输出违规清单供人工核实，不自动修改任何文件
- 硬性=[H] 规则明确可判
- 待核=[?] 启发式提示需人工确认
- 用法 `python devtools/check_coding_style.py [目录...] [--section 分节] [--hard-only]`
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from _style_checks import (  # noqa: E402
    SECTIONS,
    Finding,
    ImportGraph,
    load_files,
    run_checks,
)


def _run(targets: list[Path], sections: list[str], hard_only: bool) -> list[Finding]:
    """装载文件并按分节执行检查"""
    files = load_files(_ROOT, targets)

    # 导入图须含被检文件与 src 全量，扫子目录或非 src 目录时才能查全跨模块消费方
    by_rel = {f.rel: f for f in files}
    for f in load_files(_ROOT, [_ROOT / "src"]):
        by_rel.setdefault(f.rel, f)
    graph = ImportGraph(list(by_rel.values()))
    findings = run_checks(files, graph)
    findings = [f for f in findings if f.section in sections]
    if hard_only:
        findings = [f for f in findings if f.hard]
    return sorted(findings, key=lambda f: (SECTIONS.index(f.section), f.rel, f.line))


def _render(findings: list[Finding], sections: list[str]) -> str:
    """按选中分节分组渲染输出"""
    lines: list[str] = []
    for section in sections:
        bucket = [f for f in findings if f.section == section]
        lines.append(f"━━ {section} ━━ {len(bucket)} 条")
        if not bucket:
            lines.append("  （无违规）")
            continue
        current_rel = ""
        for f in bucket:
            if f.rel != current_rel:
                current_rel = f.rel
                lines.append(f"  {f.rel}")
            tag = "H" if f.hard else "?"
            lines.append(f"    :{f.line:<4} [{tag}] {f.message}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="按 docs/coding-style.md 扫描编码规范违规"
    )
    parser.add_argument(
        "targets", nargs="*", default=None, help="扫描目录或文件，默认 src"
    )
    parser.add_argument(
        "--section",
        action="append",
        default=None,
        choices=list(SECTIONS),
        help="只输出指定分节，可多次",
    )
    parser.add_argument("--hard-only", action="store_true", help="只输出硬性违规")
    args = parser.parse_args(argv)

    raw = args.targets or ["src"]
    targets: list[Path] = []
    for item in raw:
        path = Path(item)
        if not path.is_absolute():
            path = _ROOT / path
        if not path.exists():
            print(f"路径不存在：{path}", file=sys.stderr)
            return 2
        targets.append(path)

    sections = args.section or list(SECTIONS)
    findings = _run(targets, sections, args.hard_only)
    print(_render(findings, sections))
    hard = sum(1 for f in findings if f.hard)
    print(
        f"合计 {len(findings)} 条（硬性 {hard}，待核 {len(findings) - hard}），扫描 {len(targets)} 个目标"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
