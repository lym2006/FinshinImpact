# src/bootstrap/_plugin/_support.py
"""装库执行支撑

- 提供 uv 定位、工具配置单源与子进程执行管线，installer/assets/fingerprint 共用
- 子进程原始输出全量写运行日志，过滤调试噪音后转发进度窗
"""

import importlib.metadata
import shutil
import subprocess
import sys
import tomllib
from collections.abc import Callable
from pathlib import Path
from typing import Any

from messages import PluginMessage
from profile_env import ROOT_DIR

from ._manifest import top_package_name

# 进度回调签名，逐行接收子进程输出
ProgressFn = Callable[[str], None]

PYPROJECT = ROOT_DIR / "pyproject.toml"

RUNTIME_DIR = ROOT_DIR / "runtime"
_PY_EXE = RUNTIME_DIR / "python.exe"

# 子进程原始输出留痕，用户可见面收敛后的完整事实源
_INSTALL_LOG = RUNTIME_DIR / "plugin-ops.log"

# 调试级噪音行前缀，除这些外子进程输出一律直通进度窗
_NOISE_PREFIXES = ("DEBUG", "TRACE")

# GUI 进程派生 console 子进程会各开一个黑窗口，输出已管道捕获，窗口纯属多余
_CREATE_NO_WINDOW = 0x08000000  # 与 launcher 同值：CREATE_NO_WINDOW 标志

# 开发模式虚拟环境内的 uv 候选位置
_VENV_DIRS = (".venv", "venv", "env")

# 各 bin 目录布局对应的可执行文件名
_UV_NAMES = {"bin": "uv", "Scripts": "uv.exe"}


def _tool_settings() -> dict:
    """读 pyproject 的 [tool.finshin-impact] 表

    - 换源序列与缓存目录的单源，launcher 读同一张表
    """
    try:
        with open(PYPROJECT, "rb") as handle:
            data = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError):
        return {}
    return data.get("tool", {}).get("finshin-impact", {})


_SETTINGS = _tool_settings()


def _require(key: str) -> Any:
    """取配置表键值，缺键即报错

    - 缺键直接抛错，把配置问题暴露出来
    - 代码不写默认值，避免出现第二份不一致的副本
    """
    if key not in _SETTINGS:
        raise RuntimeError(f"pyproject 缺 [tool.finshin-impact].{key}")
    return _SETTINGS[key]


# uv 索引按序重试：国内多源轮询，最后官方源兜底
_UV_INDEX_URLS = tuple(_require("uv-index-urls"))

# 内核下载走配置镜像，失败清变量回退官方源
PLAYWRIGHT_CDN = str(_require("playwright-cdn"))

_UV_CACHE_DIR = RUNTIME_DIR / str(_require("uv-cache-dir"))


def _find_uv() -> Path | None:
    """定位可用 uv 可执行文件

    - 依次查找 runtime 目录、venv 同目录、PATH
    - 全部找不到返回 None，装库降级为打印手动命令
    """
    exe = RUNTIME_DIR / "uv.exe"
    if exe.is_file():
        return exe
    for name in _VENV_DIRS:
        for stem in ("bin", "Scripts"):
            cand = ROOT_DIR / name / stem / _UV_NAMES[stem]
            if cand.is_file():
                return cand
    return Path(uv) if (uv := shutil.which("uv")) else None


def python_target() -> str:
    """pip 子命令 --python 指向的目标解释器"""
    if _PY_EXE.is_file():
        return str(_PY_EXE)
    return str(Path(sys.executable))


# uv pip 子命令公共选项，须紧跟子命令名之后拼装
PIP_FLAGS = ["--python", python_target(), "--cache-dir", str(_UV_CACHE_DIR)]


def dev_mode() -> bool:
    """判断是否开发模式

    - 找不到任何 uv 即降级，装库只打印手动命令
    """
    return _find_uv() is None


def uv_cmd(pip_args: str) -> str:
    """生成开发模式下供手动执行的 uv 命令"""
    return f"uv {pip_args}"


def py_cmd(args: list[str]) -> str:
    """生成开发模式下供手动执行的 python -m 命令

    - 解释器路径写作 python，可直接粘贴进终端执行
    """
    return " ".join(["python", *args[1:]])


def emit(on_line: ProgressFn | None, text: str) -> None:
    """向进度回调输出一行，无回调即静默丢弃"""
    if on_line is not None:
        on_line(text)


def is_pin_installed(pin: str) -> bool:
    """判断单条依赖的顶层包是否已装"""
    try:
        importlib.metadata.distribution(top_package_name(pin))
    except importlib.metadata.PackageNotFoundError:
        return False
    return True


def degraded(commands: list[str], on_line: ProgressFn | None) -> None:
    """开发模式打印等效手动命令"""
    emit(on_line, PluginMessage.DEV_MANUAL.format(commands="\n".join(commands)))


def clean_cache(on_line: ProgressFn | None = None) -> None:
    """清除 uv 包缓存

    - 缓存放包内是为断点续装命中，装齐后留着只占磁盘
    - cache 子命令不吃 --python，只挂缓存目录配置
    """
    _run_uv(["cache", "clean", "--cache-dir", str(_UV_CACHE_DIR)], None, on_line)


def with_index_retry(args: list[str], on_line: ProgressFn | None) -> int:
    """按换源序列执行 pip 命令直至成功

    - 返回最后一次的退出码，全源落空即非零
    """
    code = 1
    for i, index in enumerate(_UV_INDEX_URLS):
        if i:
            emit(on_line, PluginMessage.INDEX_RETRY.format(try_count=i, url=index))
            emit(on_line, PluginMessage.INDEX_RETRY_NOTE)
        code = _run_uv(args, index, on_line)
        if code == 0:
            return 0
    return code


def _run_uv(
    args: list[str], index_url: str | None = None, on_line: ProgressFn | None = None
) -> int:
    """执行一次 uv 子进程并返回退出码

    - index_url 传入即挂 --index-url，清缓存类命令走 None
    """
    uv = _find_uv()
    argv = [str(uv), *args]
    if index_url:
        argv += ["--index-url", index_url]
    return run_process(argv, on_line)


def _is_noise(line: str) -> bool:
    """判断单行是否为调试噪音，其余输出转发进度窗"""
    return line.lstrip().startswith(_NOISE_PREFIXES)


def log_ops(lines: list[str]) -> None:
    """把子进程原始输出全量追加写入运行日志"""
    if not lines:
        return
    try:
        _INSTALL_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(_INSTALL_LOG, "a", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
    except OSError:
        pass


def run_process(
    argv: list[str],
    on_line: ProgressFn | None = None,
    *,
    env: dict[str, str] | None = None,
) -> int:
    """执行子进程，原始输出写日志并转发进度窗

    - 静默无窗执行，输出只进进度窗
    - stdout/stderr 合流，编码异常替换不中断
    - 非零退出时取末条失败行生成简短摘要
    """
    process = subprocess.Popen(
        argv,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        creationflags=_CREATE_NO_WINDOW,
    )
    raw: list[str] = []
    stream = process.stdout
    if stream is not None:
        for line in stream:
            stripped = line.rstrip()
            raw.append(stripped)
            if stripped and not _is_noise(stripped):
                emit(on_line, stripped)
    code = process.wait()
    log_ops(raw)
    if code != 0 and on_line is not None:
        last_err = next(
            (ln for ln in reversed(raw) if ln and not _is_noise(ln)), ""
        )
        reason = last_err[:80] if last_err else PluginMessage.PROC_FAIL_FALLBACK
        emit(on_line, PluginMessage.PROC_FAIL.format(reason=reason))
    return code
