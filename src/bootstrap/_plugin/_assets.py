# src/bootstrap/_plugin/_assets.py
"""非 pip 资源安装

- playwright 内核等资源通过模块子命令安装，声明按模块名与资源名两段拼 argv
- 镜像下载失败时清除环境变量回退官方源
"""

import os

from messages import PluginMessage

from ._support import (
    PLAYWRIGHT_CDN,
    ProgressFn,
    degraded,
    dev_mode,
    emit,
    py_cmd,
    python_target,
    run_process,
)


def install_assets(assets: list[str], on_line: ProgressFn | None = None) -> list[str]:
    """下载非 pip 资源并返回失败清单

    - asset 值 = 模块名与资源名两段，拼 [-m, 模块, install, 资源]
    - ⚠️ 必须晚于同批 deps 安装：-m playwright 要求 playwright 已存在
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
    """拆两段式 asset 值为安装 argv

    - 空格分词必须恰为 模块名+资源名 两段，否则返回 None
    """
    parts = asset.split()
    if len(parts) != 2:
        return None
    module, res = parts
    return [str(python_target()), "-m", module, "install", res]
