"""插件装库器

- 子进程驱动 uv 装卸插件依赖
- 同步依赖先 compile 闭包再 sync，已装 dev 工具与解释器基建并入保留清单
- 装完即编字节码，下次启动导入直接命中缓存
"""

import tempfile
from collections.abc import Sequence
from pathlib import Path

from skin.messages import PlatformMessage, PluginMessage
from system.profile_env import ROOT_DIR
from system.tool_settings import project_value

from .deps_keep import dev_dependencies
from .subprocess_ops import (
    ProgressCallback,
    degraded,
    emit,
    is_pin_installed,
    with_index_retry,
)
from .toolchain import PIP_FLAGS, dev_mode, uv_cmd

# 同步用的两份清单名
_REQUIREMENTS_IN = "requirements.in"
_REQUIREMENTS_LOCK = "requirements.txt"


def remove_distributions(
    names: Sequence[str], on_line: ProgressCallback | None = None
) -> list[str]:
    """从运行环境卸掉点名的发行件，交出卸不掉的说明行

    - 一条命令带全部名，整批失败转逐只重试并逐只点名
    - 开发模式只交等效手动命令
    """
    wanted = list(names)
    if not wanted:
        return []
    if dev_mode():
        degraded([uv_cmd(f"pip uninstall {' '.join(wanted)}")], on_line)
        return [PlatformMessage.REMOVE_FAILED.format(name=name) for name in wanted]

    base = ["pip", "uninstall", *PIP_FLAGS, "--no-progress"]
    if with_index_retry([*base, *wanted], on_line) == 0:
        return []

    failed: list[str] = []
    for name in wanted:
        if with_index_retry([*base, name], on_line) != 0:
            failed.append(PlatformMessage.REMOVE_FAILED.format(name=name))

    return failed


def install_deps(pins: list[str], on_line: ProgressCallback | None = None) -> list[str]:
    """安装依赖并返回失败清单

    - 整批安装走换源序列，整批失败转逐包重试收集差集
    - uv 会跳过已安装的包，重复调用即自动续装
    """
    if not pins:
        return []
    if dev_mode():
        degraded([uv_cmd(f"pip install --compile-bytecode {' '.join(pins)}")], on_line)
        return list(pins)
    base = [
        "pip",
        "install",
        *PIP_FLAGS,
        "--link-mode",
        "copy",
        "--no-progress",
        "--compile-bytecode",
    ]
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
    return [pin for pin in dev_dependencies() if is_pin_installed(pin)]


def _interpreter_pins() -> list[str]:
    """取解释器基建包的已装版本 pin"""
    # sync 会删除清单外的包，不保留连解释器管理件也会被删
    # 冷盘元数据导入上百毫秒，首次同步才付
    import importlib.metadata

    pins: list[str] = []
    for name in ("pip", "setuptools"):
        try:
            pins.append(f"{name}=={importlib.metadata.version(name)}")
        except importlib.metadata.PackageNotFoundError:
            continue
    return pins


def _editable_project_pin() -> list[str]:
    """取项目自身的 editable 安装条目

    - 发布 runtime 无此元数据，返回空表即不追加
    """
    name = project_value("name")
    if not name:
        return []
    if not is_pin_installed(name):
        return []

    # sync 不保留会连项目自身的 editable 安装一起删
    return [f"-e {ROOT_DIR}"]


def sync_env(
    keep: list[str],
    on_line: ProgressCallback | None = None,
    notes: list[str] | None = None,
) -> list[str]:
    """按保留清单重建环境并返回失败清单

    - 装库前播报清单矛盾的说明行
    - 先 compile 出含传递依赖的闭包再喂 sync
    - 已装 dev 工具、项目 editable 安装、解释器基建并入保留清单
    - 整批执行，失败时失败清单为保留清单全体
    - 会删除保留清单外的包，调用方须先向用户确认
    """
    for note in notes or ():
        emit(on_line, note)
    if dev_mode():
        emit(on_line, PluginMessage.DEV_SYNC)
        return list(keep)
    argv_keep = [
        *keep,
        *_installed_dev_pins(),
        *_editable_project_pin(),
        *_interpreter_pins(),
    ]
    with tempfile.TemporaryDirectory(prefix="finshin-sync-") as stage:
        pins_path = Path(stage) / _REQUIREMENTS_IN
        pins_path.write_text("\n".join(argv_keep), encoding="utf-8")
        lock_path = Path(stage) / _REQUIREMENTS_LOCK

        # uv pip sync 不做依赖解析，直喂顶层 pin 会删掉全部传递依赖
        compile_argv = [
            "pip",
            "compile",
            str(pins_path),
            *PIP_FLAGS,
            "--no-header",
            "-q",
            "-o",
            str(lock_path),
        ]
        emit(on_line, PluginMessage.STAGE_COMPILE)
        if with_index_retry(compile_argv, on_line) != 0:
            return list(keep)
        sync_argv = [
            "pip",
            "sync",
            *PIP_FLAGS,
            "--no-progress",
            "--compile-bytecode",
            str(lock_path),
        ]
        emit(on_line, PluginMessage.STAGE_SYNC)
        code = with_index_retry(sync_argv, on_line)
    if code != 0:
        return list(keep)
    return []
