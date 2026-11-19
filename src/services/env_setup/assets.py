"""非 pip 资源安装

- 资源通过模块子命令安装，声明按模块名与资源名两段拼命令参数
- 镜像下载失败时清除环境变量回退官方源
- 落盘探活走 dry-run 取权威安装目录逐个复核
"""

import os
from pathlib import Path

from skin.messages import PluginMessage

from .subprocess_ops import (
    ProgressCallback,
    capture_output,
    degraded,
    emit,
    run_process,
)
from .toolchain import PLAYWRIGHT_CDN, dev_mode, py_cmd, python_target

# dry-run 行内"Install location: 路径"的定位前缀
_LOCATION_MARK = "Install location:"


def _install_dirs(module: str, res: str) -> list[str]:
    """经 dry-run 取资源的权威安装目录清单"""
    # 这趟子进程要一秒上下，只在确有资源要判时才付
    # 内核会把随附件一并列出，全查不收窄
    argv = [str(python_target()), "-m", module, "install", "--dry-run", res]
    locs: list[str] = []
    for line in capture_output(argv).splitlines():
        stripped = line.strip()
        if stripped.startswith(_LOCATION_MARK):
            locs.append(stripped[len(_LOCATION_MARK) :].strip())
    return locs


def is_asset_installed(asset: str) -> bool:
    """判断资源是否已落盘

    - 走 dry-run 取权威目录，逐个存在才算已装
    """
    parts = asset.split()
    if len(parts) != 2:
        return False
    module, res = parts
    locs = _install_dirs(module, res)
    return bool(locs) and all(Path(loc).is_dir() for loc in locs)


def install_assets(
    assets: list[str], on_line: ProgressCallback | None = None
) -> list[str]:
    """下载非 pip 资源并返回失败清单

    - 资源声明由模块名与资源名两段组成
    - 必须晚于同批依赖安装
    """
    failed: list[str] = []
    for asset in assets:
        argv = _install_argv(asset)
        if argv is None:
            emit(on_line, PluginMessage.ASSET_BAD.format(asset=asset))
            failed.append(asset)
            continue
        if dev_mode():
            degraded([py_cmd(argv[1:])], on_line)
            failed.append(asset)
            continue
        env = os.environ.copy()
        env["PLAYWRIGHT_DOWNLOAD_HOST"] = PLAYWRIGHT_CDN
        if run_process(argv, on_line, env=env) == 0:
            continue
        emit(on_line, PluginMessage.CDN_FALLBACK)
        del env["PLAYWRIGHT_DOWNLOAD_HOST"]
        if run_process(argv, on_line, env=env) != 0:
            failed.append(asset)
    return failed


def _install_argv(asset: str) -> list[str] | None:
    """拆两段式资源声明为安装参数

    - 空格分词恰为模块名与资源名两段，否则交出 None
    """
    parts = asset.split()
    if len(parts) != 2:
        return None
    module, res = parts
    return [str(python_target()), "-m", module, "install", res]
