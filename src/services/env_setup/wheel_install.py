"""wheel 发行件装进运行环境

- 一条命令带全部 wheel 与 --find-links，本地包互相喂依赖
- 整批失败转逐只重试，收集装不进的发行件
"""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from skin.messages import CatalogMessage

from .subprocess_ops import ProgressCallback, degraded, with_index_retry
from .toolchain import PIP_FLAGS, WHEELS_DIR, dev_mode, uv_cmd


@dataclass(frozen=True, slots=True)
class WheelFile:
    """一只落到盘上的 wheel 件

    - distribution 用于点名，path 用于交给 uv
    """

    distribution: str
    path: Path


def _install_flags() -> list[str]:
    """拼一次装 wheel 的 uv 参数"""
    return [
        "pip",
        "install",
        *PIP_FLAGS,
        "--find-links",
        str(WHEELS_DIR),
        "--link-mode",
        "copy",
        "--no-progress",
        "--compile-bytecode",
    ]


def install_releases(
    files: Sequence[WheelFile], on_line: ProgressCallback | None = None
) -> list[str]:
    """把 wheel 装进运行环境，交出装不进的说明行

    - 一条命令带全部件，本地包互相喂依赖
    - 整批失败转逐只重试，逐只点名
    - 开发模式只交等效手动命令
    """
    if not files:
        return []

    paths = [str(item.path) for item in files]
    if dev_mode():
        degraded(
            [uv_cmd(f"pip install --find-links {WHEELS_DIR} " + " ".join(paths))],
            on_line,
        )
        return [
            CatalogMessage.INSTALL_FAILED.format(name=item.distribution)
            for item in files
        ]

    base = _install_flags()
    if with_index_retry([*base, *paths], on_line) == 0:
        return []

    failed: list[str] = []
    for item in files:
        if with_index_retry([*base, str(item.path)], on_line) != 0:
            failed.append(CatalogMessage.INSTALL_FAILED.format(name=item.distribution))

    return failed
