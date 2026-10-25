# devtools/_style_checks/_s5d_access.py
"""跨包私有访问检查

- 导入路径含 `_` 前缀模块段且消费方在宿主包树外即违规
- 宿主包树内互用豁免，私有性边界止于宿主包
- 符号级下划线归 _s5_naming，本档只管模块路径级越界
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ._common import Finding, ImportGraph

if TYPE_CHECKING:
    from ._common import FileData


def check(files: list[FileData], graph: ImportGraph) -> list[Finding]:
    """扫描跨包导入私有模块的违规"""
    by_module = {f.module: f for f in files if f.module}
    findings: list[Finding] = []
    seen: set[tuple[str, str, int]] = set()
    for importer, target, lineno in graph.edges:
        file = by_module.get(importer)
        if file is None:
            continue
        findings.extend(_check_edge(file, importer, target, lineno, seen))
    return findings


def _check_edge(
    file: FileData,
    importer: str,
    target: str,
    lineno: int,
    seen: set[tuple[str, str, int]],
) -> list[Finding]:
    """单条导入边内逐个下划线段做越界判定"""
    findings: list[Finding] = []
    parts = target.split(".")
    for i, seg in enumerate(parts):
        if not seg.startswith("_"):
            continue
        priv = ".".join(parts[: i + 1])
        holder = priv.rpartition(".")[0]
        if not holder:
            continue
        if importer == priv or importer.startswith(f"{priv}."):
            continue
        if importer == holder or importer.startswith(f"{holder}."):
            continue
        key = (importer, priv, lineno)
        if key in seen:
            continue
        seen.add(key)
        findings.append(
            Finding(
                "命名与门面导出",
                file.rel,
                lineno,
                f"跨包访问私有模块 `{priv}`，消费方 `{importer}` 在宿主包 `{holder}` 之外",
                True,
            )
        )
    return findings
