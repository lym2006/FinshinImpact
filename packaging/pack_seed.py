"""随包接口件

- 构建时现打接口包 wheel，拷进发布目录的接口件目录
- 源码不在场即当场停下，发布物没有它起不来
"""

import shutil
import subprocess
from pathlib import Path

from pack_spec import ROOT, STAGE, PackLayout, local_version

# 接口包源码与产物目录
_SDK_SOURCE = ROOT / "finshin" / "sdk"
_DIST_DIR = "dist"
_WHEEL_GLOB = "*.whl"


def _find_uv() -> Path:
    """定位可用的 uv 可执行文件

    - 系统搜索路径与开发虚拟环境各认一处
    """
    found = shutil.which("uv")
    if found:
        return Path(found)
    for stem, exe in ((".venv/Scripts", "uv.exe"), (".venv/bin", "uv")):
        cand = ROOT / stem / exe
        if cand.is_file():
            return cand

    raise RuntimeError("找不到 uv，打不出随包的接口件")


def seed_sdk_wheel() -> None:
    """把接口包 wheel 打进发布目录

    - 版本与文件名取自接口包自己的声明
    - 升级整目录替换，装过的那一份留在 runtime 里不动
    """
    if not _SDK_SOURCE.is_dir():
        raise RuntimeError(f"找不到接口包源码 {_SDK_SOURCE}，先按开发手册挂载子仓")

    subprocess.run(
        [str(_find_uv()), "build", str(_SDK_SOURCE), "--wheel"],
        check=True,
        capture_output=True,
    )
    version = local_version(_SDK_SOURCE)
    fresh = [
        wheel
        for wheel in (_SDK_SOURCE / _DIST_DIR).glob(_WHEEL_GLOB)
        if f"-{version}-" in wheel.name
    ]
    if not fresh:
        raise RuntimeError(f"接口包 dist 里没有 {version} 的 wheel")

    target = STAGE / PackLayout.SDK_WHEEL_DIR
    target.mkdir(parents=True, exist_ok=True)
    chosen = max(fresh, key=lambda wheel: wheel.stat().st_mtime)
    shutil.copy2(chosen, target / chosen.name)
