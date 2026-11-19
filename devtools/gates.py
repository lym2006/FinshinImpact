r"""五项闸门执行器

- 目标由一次动态发现算出：本体三棵树加挂载子仓的源码与用例目录
- 子仓认装载根下声明文件里 package-dir 那项改名映射，新增挂载不必改这里
- 每步一行读数，任一步红即非零退出
- 用法 `python devtools/gates.py [--only 步名]...`，缺省跑齐五步
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tomllib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent

_MAIN_TARGETS = ("src", "packaging", "devtools")
_MOUNT_ROOT = "finshin"
_IGNORED_PARTS = frozenset({"build", "dist", "__pycache__", ".git", "egg-info"})

_STEPS = ("ruff", "pyright", "imports", "style", "pytest")

_IS_WINDOWS = os.name == "nt"

# 虚拟环境的脚本目录名与可执行文件后缀，Windows 侧换 Scripts 加 exe
_VENV_SCRIPTS_DIR = "Scripts" if _IS_WINDOWS else "bin"
_EXE_SUFFIX = ".exe" if _IS_WINDOWS else ""

# lint-imports、扫描器与 pytest 三步按源码目录导入，须带这两个变量起
_DOC_ENV = {"PYTHONUTF8": "1", "PYTHONPATH": "src"}
_FAIL_TAIL_LINES = 30
_RC_NOT_FOUND = 127  # shell 约定，命令找不到时的退出码


@dataclass(frozen=True)
class _Subrepo:
    """一只按改名声明发现的挂载子仓"""

    rel: str
    sources: tuple[str, ...]
    tests: str | None


@dataclass(frozen=True)
class _StepResult:
    """单步读数，含是否绿、一行数字、红时供截尾的原始输出"""

    ok: bool
    detail: str
    output: str


def _discover_subrepos(root: Path) -> tuple[_Subrepo, ...]:
    """装载根下逐份声明文件找子仓，带 package-dir 改名映射的才算"""
    mounts = root / _MOUNT_ROOT
    if not mounts.is_dir():
        return ()
    found: list[_Subrepo] = []
    for cfg in sorted(mounts.rglob("pyproject.toml")):
        if _IGNORED_PARTS & set(cfg.relative_to(mounts).parts):
            continue
        dirs = _package_dirs(cfg)
        if not dirs:
            continue
        rel = cfg.parent.relative_to(root).as_posix()
        sources = tuple(sorted(f"{rel}/{d}" for d in dirs))
        tests = f"{rel}/tests" if (cfg.parent / "tests").is_dir() else None
        found.append(_Subrepo(rel, sources, tests))
    return tuple(found)


def _package_dirs(cfg: Path) -> tuple[str, ...]:
    """读声明里的包名到目录映射，缺项或读不动回空表"""
    try:
        data = tomllib.loads(cfg.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return ()
    mapping = data.get("tool", {}).get("setuptools", {}).get("package-dir") or {}
    return tuple(sorted({str(v) for v in mapping.values() if str(v).strip("./")}))


def _subrepo_sources(root: Path) -> tuple[str, ...]:
    """各发现到的子仓源码目录，没挂载时回空表"""
    return tuple(sorted(d for sub in _discover_subrepos(root) for d in sub.sources))


def _source_targets(root: Path) -> tuple[str, ...]:
    """源码类步的目标，本体三棵树加挂载子仓的源码目录"""
    return (*_MAIN_TARGETS, *_subrepo_sources(root))


def _pytest_targets(root: Path) -> tuple[str, ...]:
    """用例目标，本体用例树加各带用例目录的子仓"""
    extra = [sub.tests for sub in _discover_subrepos(root) if sub.tests]
    return ("devtools/tests", *sorted(extra))


def _venv_tool(name: str) -> str:
    """虚拟环境里的工具路径，按平台补脚本目录与 exe 后缀"""
    return str(_ROOT / ".venv" / _VENV_SCRIPTS_DIR / f"{name}{_EXE_SUFFIX}")


def _execute(cmd: list[str], env: dict[str, str] | None = None) -> tuple[int, str]:
    """仓根起子进程，合流回退出码与文本"""
    merged = {**os.environ, **(env or {})}
    try:
        proc = subprocess.run(
            cmd,
            cwd=_ROOT,
            env=merged,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError as error:
        return _RC_NOT_FOUND, f"起不动：{error}"
    return proc.returncode, ((proc.stdout or "") + (proc.stderr or "")).strip()


def _match_int(pattern: str, text: str) -> str:
    """从输出抓一个数字读数，抓不到回问号"""
    hit = re.search(pattern, text)
    return hit.group(1) if hit else "?"


def _step_ruff() -> _StepResult:
    """格式与静态检查两步合一，都只检查不改写"""
    ruff = _venv_tool("ruff")
    code_fmt, text_fmt = _execute([ruff, "format", "--check", "."])
    code_chk, text_chk = _execute([ruff, "check", "."])
    combined = f"{text_fmt}\n{text_chk}".strip()
    fmt = text_fmt.count("Would reformat:") if code_fmt else 0
    chk = _match_int(r"Found (\d+) error", text_chk) if code_chk else 0
    ok = code_fmt == 0 and code_chk == 0
    return _StepResult(ok, f"format {fmt} / check {chk}", combined)


def _step_pyright() -> _StepResult:
    """类型检查，跑开发依赖随装的 pyright"""
    cmd = [
        _venv_tool("pyright"),
        "--pythonpath",
        _venv_tool("python"),
        "--project",
        "pyrightconfig.json",
        *_source_targets(_ROOT),
    ]
    code, text = _execute(cmd)
    errors = _match_int(r"(\d+) errors", text)
    return _StepResult(code == 0, f"errors {errors}", text)


def _step_imports() -> _StepResult:
    """分层契约检查"""
    code, text = _execute([_venv_tool("lint-imports")], _DOC_ENV)
    broken = _match_int(r"(\d+) broken", text)
    return _StepResult(code == 0, f"broken {broken}", text)


def _step_style() -> _StepResult:
    """编码规范扫描器扫本体三棵树与挂载子仓的源码目录"""
    cmd = [
        _venv_tool("python"),
        "devtools/check_coding_style.py",
        *_source_targets(_ROOT),
    ]
    code, text = _execute(cmd, _DOC_ENV)
    hard = _match_int(r"硬性 (\d+)", text)
    soft = _match_int(r"待核 (\d+)", text)
    ok = code == 0 and hard == "0"
    return _StepResult(ok, f"硬性 {hard} / 待核 {soft}", text)


def _step_pytest() -> _StepResult:
    """用例全量跑"""
    cmd = [_venv_tool("pytest"), *_pytest_targets(_ROOT), "-q"]
    code, text = _execute(cmd, _DOC_ENV)
    passed = _match_int(r"(\d+) passed", text)
    return _StepResult(code == 0, f"passed {passed}", text)


_STEP_FUNCS: dict[str, Callable[[], _StepResult]] = {
    "ruff": _step_ruff,
    "pyright": _step_pyright,
    "imports": _step_imports,
    "style": _step_style,
    "pytest": _step_pytest,
}


def _run_step(name: str) -> _StepResult:
    """按步名执行对应的一步"""
    return _STEP_FUNCS[name]()


def _report(results: list[tuple[str, _StepResult]]) -> int:
    """每步一行读数，红步追一段原始输出截尾，回进程退出码"""
    failed = [name for name, res in results if not res.ok]
    for name, res in results:
        print(f"{name:<8} {'PASS' if res.ok else 'FAIL'}  {res.detail}")
        if not res.ok:
            for line in res.output.splitlines()[-_FAIL_TAIL_LINES:]:
                print(f"  | {line}")
    return 1 if failed else 0


def main(
    argv: list[str] | None = None,
    *,
    dispatch: Callable[[str], _StepResult] | None = None,
) -> int:
    """选择要跑的步并按序执行，dispatch 是用例注入的替身口子"""
    parser = argparse.ArgumentParser(description="跑齐五项闸门，每步一行读数")
    parser.add_argument(
        "--only",
        action="append",
        choices=list(_STEPS),
        help=f"只跑指定步，可多次，候选 {'/'.join(_STEPS)}",
    )
    args = parser.parse_args(argv)
    runner = dispatch if dispatch is not None else _run_step
    chosen = args.only or list(_STEPS)
    return _report([(name, runner(name)) for name in chosen])


if __name__ == "__main__":
    sys.exit(main())
