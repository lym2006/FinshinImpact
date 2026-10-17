# src/bootstrap/_plugin/_support.py
"""装库执行支撑

- 子进程执行管线：换源重试、噪音过滤、心跳补行、原始输出落运行日志
- 环境定位与工具配置读取在 _env
"""

import importlib.metadata
import threading
from collections.abc import Callable

from skin.messages import PluginMessage
from system.proc import popen_hidden, run_hidden

from ._env import (
    RUNTIME_DIR,
    UV_CACHE_DIR,
    UV_INDEX_URLS,
    dev_mode,
    find_uv,
    uv_cmd,
)
from ._manifest import top_package_name

# 进度回调签名，逐行接收子进程输出
ProgressCallback = Callable[[str], None]

# 子进程原始输出留痕，用户可见面收敛后的完整事实源
_INSTALL_LOG = RUNTIME_DIR / "plugin-ops.log"

# 调试级噪音行前缀，除这些外子进程输出一律直通进度窗
_NOISE_PREFIXES = ("DEBUG", "TRACE")

# 子进程静默多久刷一次等待秒数（秒）
_HEARTBEAT_INTERVAL = 1

# 心跳线程收尾等待上限（秒）
_HEARTBEAT_JOIN_TIMEOUT = 2


def emit(on_line: ProgressCallback | None, text: str) -> None:
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


def degraded(commands: list[str], on_line: ProgressCallback | None) -> None:
    """开发模式打印等效手动命令"""
    emit(on_line, PluginMessage.DEV_MANUAL.format(commands="\n".join(commands)))


def clean_cache(on_line: ProgressCallback | None = None) -> None:
    """清除 uv 包缓存

    - 缓存放包内是为断点续装命中，装齐后留着只占磁盘
    - cache 子命令不吃 --python，只挂缓存目录配置
    - 开发模式无 uv，降级为打印等效手动命令
    """
    if dev_mode():
        degraded([uv_cmd(f"cache clean --cache-dir {UV_CACHE_DIR}")], on_line)
        return
    _run_uv(["cache", "clean", "--cache-dir", str(UV_CACHE_DIR)], None, on_line)


def with_index_retry(args: list[str], on_line: ProgressCallback | None) -> int:
    """按换源序列执行 pip 命令直至成功

    - 返回最后一次的退出码，全源落空即非零
    """
    code = 1
    for i, index in enumerate(UV_INDEX_URLS):
        if i:
            emit(on_line, PluginMessage.INDEX_RETRY.format(try_count=i, url=index))
            emit(on_line, PluginMessage.INDEX_RETRY_NOTE)
        code = _run_uv(args, index, on_line)
        if code == 0:
            return 0
    return code


def _run_uv(
    args: list[str],
    index_url: str | None = None,
    on_line: ProgressCallback | None = None,
) -> int:
    """执行一次 uv 子进程并返回退出码

    - index_url 传入即挂 --index-url，清缓存类命令走 None
    """
    argv = [str(find_uv()), *args]
    if index_url:
        argv += ["--index-url", index_url]
    return run_process(argv, on_line)


def _is_noise(line: str) -> bool:
    """判断单行是否为调试噪音，其余输出转发进度窗"""
    return line.lstrip().startswith(_NOISE_PREFIXES)


class _Heartbeat(threading.Thread):
    """子进程静默心跳

    - 持续无输出按间隔发一行等待提示
    - 原位刷新由进度窗渲染层负责，主侧收到任何输出即重置计时
    """

    def __init__(self, on_line: ProgressCallback | None) -> None:
        super().__init__(daemon=True, name="InstallHeartbeat")
        self._on_line = on_line
        self._halted = threading.Event()
        self._tick = threading.Event()
        self._seconds = 0

    def touch(self) -> None:
        """宣告当前静默期结束，心跳归零"""
        self._seconds = 0
        self._tick.set()

    def halt(self) -> None:
        """请求线程退出"""
        self._halted.set()
        self._tick.set()

    def run(self) -> None:
        while not self._halted.is_set():
            self._tick.clear()
            if self._tick.wait(_HEARTBEAT_INTERVAL):
                continue
            self._seconds += _HEARTBEAT_INTERVAL
            emit(self._on_line, PluginMessage.HEARTBEAT.format(seconds=self._seconds))


def _join_heartbeat(beat: _Heartbeat | None) -> None:
    """停心跳并等线程收尾"""
    if beat is None:
        return
    beat.halt()
    beat.join(timeout=_HEARTBEAT_JOIN_TIMEOUT)


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
    on_line: ProgressCallback | None = None,
    *,
    env: dict[str, str] | None = None,
) -> int:
    """执行子进程，原始输出写日志并转发进度窗

    - 静默无窗执行，输出只进进度窗
    - stdout/stderr 合流，编码异常替换不中断
    - 持续无输出由心跳补等待行，任务结束即停
    - 非零退出时取末条失败行生成简短摘要
    """
    process = popen_hidden(argv, env)
    raw: list[str] = []
    beat = _Heartbeat(on_line) if on_line is not None else None
    if beat is not None:
        beat.start()
    stream = process.stdout
    if stream is not None:
        for line in stream:
            stripped = line.rstrip()
            raw.append(stripped)
            if stripped and not _is_noise(stripped):
                if beat is not None:
                    beat.touch()
                emit(on_line, stripped)
    code = process.wait()
    _join_heartbeat(beat)
    log_ops(raw)
    if code != 0 and on_line is not None:
        last_err = next((ln for ln in reversed(raw) if ln and not _is_noise(ln)), "")
        reason = last_err[:80] if last_err else PluginMessage.PROC_FAIL_FALLBACK
        emit(on_line, PluginMessage.PROC_FAIL.format(reason=reason))
    return code


def capture_output(argv: list[str]) -> str:
    """执行子进程并回取全部输出

    - 探测类短命令专用：不落日志、不起心跳，失败一律回空串
    - 调用方按输出内容判定，退出码不单独表达结论
    """
    try:
        done = run_hidden(argv)
    except OSError:
        return ""
    return done.stdout if done.returncode == 0 else ""
