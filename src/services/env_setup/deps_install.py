# src/services/env_setup/deps_install.py
"""插件装库器

- 子进程驱动 uv 装卸插件依赖
- 同步依赖先 compile 闭包再 sync，已装 dev 工具与解释器基建并入保留清单
- 装完即编字节码，下次启动导入直接命中缓存
- 同步成功落对账戳，启动期据此判断要不要提示同步
"""

import hashlib
import tempfile
import tomllib
from pathlib import Path

from skin.messages import PluginMessage
from system.profile_env import ROOT_DIR

from .deps_manifest import dev_dependencies, keep_union
from .subprocess_ops import (
    ProgressCallback,
    degraded,
    emit,
    is_pin_installed,
    with_index_retry,
)
from .toolchain import PIP_FLAGS, PYPROJECT, RUNTIME_DIR, dev_mode, uv_cmd

# 依赖对账戳，记声明清单指纹，与启动器记装没装过的 .installed 各说一件事
_SYNC_STAMP = RUNTIME_DIR / ".synced"


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
    """取解释器基建包的已装版本 pin

    - pip/setuptools 随 venv 创建而来，不属任何依赖清单
    - 发布包的嵌入式 Python 可能没有这些包，缺失即不注入
    - sync 会删除清单外的包，不保留连解释器管理件也会被删
    """
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

    - 开发 venv 里装过 -e，sync 不保留会连项目安装一起删
    - 发布 runtime 无此元数据，返回空表即不追加
    """
    try:
        with open(PYPROJECT, "rb") as handle:
            name = str(tomllib.load(handle)["project"]["name"])
    except (OSError, tomllib.TOMLDecodeError, KeyError):
        return []
    if not is_pin_installed(name):
        return []
    return [f"-e {ROOT_DIR}"]


def _keep_digest(keep: list[str]) -> str:
    """声明清单指纹

    - 排序去重，扫描顺序或重复声明变动不误判为待同步
    """
    return hashlib.sha256("\n".join(sorted(set(keep))).encode("utf-8")).hexdigest()


def _write_stamp(digest: str) -> None:
    """落对账戳

    - 写不进即视作未对账，下次启动再提示，与运行日志留痕同取舍
    """
    try:
        _SYNC_STAMP.parent.mkdir(parents=True, exist_ok=True)
        _SYNC_STAMP.write_text(digest, encoding="utf-8")
    except OSError:
        pass


def sync_needed() -> bool:
    """判断声明清单与对账戳是否相符

    - 只比声明清单与戳，不实测盘上装了哪些包
    - 找不到任何 uv 时按降级手动命令处理，不判同步
    - 戳缺失即从未对过账，此时按需要同步处理
    """
    if dev_mode():
        return False
    digest = _keep_digest(keep_union())
    try:
        return _SYNC_STAMP.read_text(encoding="utf-8") != digest
    except OSError:
        return True


def sync_env(keep: list[str], on_line: ProgressCallback | None = None) -> list[str]:
    """按保留清单重建环境并返回失败清单

    - 先 compile 出含传递依赖的闭包再喂 sync
    - 已装 dev 工具、项目 editable 安装、解释器基建并入保留清单
    - 整批执行，失败时失败清单为保留清单全体
    - 会删除保留清单外的包，调用方须先向用户确认
    - 成功即按声明清单落对账戳，追加项不进指纹
    """
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
        pins_path = Path(stage) / "requirements.in"
        pins_path.write_text("\n".join(argv_keep), encoding="utf-8")
        lock_path = Path(stage) / "requirements.txt"

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
    _write_stamp(_keep_digest(keep))
    return []
