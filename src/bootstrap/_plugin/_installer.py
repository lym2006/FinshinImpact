# src/bootstrap/_plugin/_installer.py
"""插件装库器

- 子进程驱动 uv 装卸插件依赖，环境定位与执行管线在 _support
- 资源装卸拆至 _assets，已装指纹拆至 _fingerprint，启动结算编排拆至 _startup
- 同步依赖先 compile 闭包再 sync，已装 dev 工具与解释器基建并入保留清单
"""

import importlib.metadata
import tempfile
import tomllib
from pathlib import Path

from messages import PluginMessage
from profile_env import ROOT_DIR

from ._manifest import dev_dependencies, top_package_name
from ._support import (
    PIP_FLAGS,
    PYPROJECT,
    ProgressFn,
    degraded,
    dev_mode,
    emit,
    uv_cmd,
    with_index_retry,
)


def install_deps(pins: list[str], on_line: ProgressFn | None = None) -> list[str]:
    """安装依赖并返回失败清单

    - 整批安装走换源序列，整批失败转逐包重试收集差集
    - uv 会跳过已安装的包，重复调用即自动续装
    """
    if not pins:
        return []
    if dev_mode():
        degraded([uv_cmd(f"pip install {' '.join(pins)}")], on_line)
        return list(pins)
    base = ["pip", "install", *PIP_FLAGS, "--link-mode", "copy", "--no-progress"]
    if with_index_retry([*base, *pins], on_line) == 0:
        return []
    failed: list[str] = []
    for pin in pins:
        if with_index_retry([*base, pin], on_line) != 0:
            failed.append(pin)
    return failed


def _installed_dev_pins() -> list[str]:
    """取 dev 可选依赖里已安装的 pin

    - 同步属环境运维，装了的开发工具不许被删
    - 未安装者不追加，避免 sync 顺带强装
    """
    pins: list[str] = []
    for pin in dev_dependencies():
        try:
            importlib.metadata.distribution(top_package_name(pin))
        except importlib.metadata.PackageNotFoundError:
            continue
        pins.append(pin)
    return pins


def _interpreter_pins() -> list[str]:
    """取解释器基建包的已装版本 pin

    - pip/setuptools 随 venv 创建而来，不属任何依赖清单
    - 发布包的嵌入式 Python 可能没有这些包，缺失即不注入
    - sync 会删除清单外的包，不保留连解释器管理件也会被删
    """
    pins: list[str] = []
    for name in ("pip", "setuptools"):
        try:
            pins.append(f"{name}=={importlib.metadata.version(name)}")
        except importlib.metadata.PackageNotFoundError:
            continue
    return pins


def _editable_project_pin() -> list[str]:
    """取项目自身的 editable 安装条目

    - 开发 venv 里装过 -e，sync 不保留会连项目安装一起删
    - 发布 runtime 无此元数据，返回空表即不追加
    """
    try:
        with open(PYPROJECT, "rb") as handle:
            name = str(tomllib.load(handle)["project"]["name"])
    except (OSError, tomllib.TOMLDecodeError, KeyError):
        return []
    try:
        importlib.metadata.distribution(name)
    except importlib.metadata.PackageNotFoundError:
        return []
    return [f"-e {ROOT_DIR}"]


def sync_env(keep: list[str], on_line: ProgressFn | None = None) -> list[str]:
    """按保留清单重建环境并返回失败清单

    - uv pip sync 不做依赖解析，直喂顶层 pin 会误删全部传递依赖
    - 先 compile 出含传递依赖的闭包再喂 sync
    - 已装 dev 工具、项目 editable 安装、解释器基建并入保留清单
    - 整批执行，失败时失败清单为保留清单全体
    - 耗时较长且会删除清单外的包，调用方须先向用户确认
    """
    if dev_mode():
        emit(on_line, PluginMessage.DEV_SYNC)
        return list(keep)
    keep = [
        *keep,
        *_installed_dev_pins(),
        *_editable_project_pin(),
        *_interpreter_pins(),
    ]
    with tempfile.TemporaryDirectory(prefix="finshin-sync-") as stage:
        pins_path = Path(stage) / "requirements.in"
        pins_path.write_text("\n".join(keep), encoding="utf-8")
        lock_path = Path(stage) / "requirements.txt"
        compile_argv = [
            "pip",
            "compile",
            str(pins_path),
            *PIP_FLAGS,
            "--no-header",
            "-o",
            str(lock_path),
        ]
        if with_index_retry(compile_argv, on_line) != 0:
            return list(keep)
        sync_argv = ["pip", "sync", *PIP_FLAGS, "--no-progress", str(lock_path)]
        code = with_index_retry(sync_argv, on_line)
    return [] if code == 0 else list(keep)
