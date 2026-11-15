"""装库环境定位

- 定位嵌入式解释器与 uv 可执行文件
- 读取换源序列与缓存目录配置
"""

import shutil
import sys
from pathlib import Path

from system.profile_env import ROOT_DIR
from system.tool_settings import tool_setting

# 包内运行目录与可执行文件名，与启动器 PackLayout 同值，两处改名必须同步
_RUNTIME_DIR_NAME = "runtime"
_PYTHON_EXE_NAME = "python.exe"
_UV_TOOL_NAME = "uv"
_UV_EXE_NAME = "uv.exe"

RUNTIME_DIR = ROOT_DIR / _RUNTIME_DIR_NAME
_PY_EXE = RUNTIME_DIR / _PYTHON_EXE_NAME

# 开发模式虚拟环境内的 uv 候选位置
_VENV_DIRS = (".venv", "venv", "env")

# 各 bin 目录布局对应的可执行文件名
_UV_NAMES = {"bin": _UV_TOOL_NAME, "Scripts": _UV_EXE_NAME}


# uv 索引按序重试：国内多源轮询，最后官方源兜底
UV_INDEX_URLS = tuple(tool_setting("uv-index-urls"))

# 内核下载走配置镜像，失败清变量回退官方源
PLAYWRIGHT_CDN = str(tool_setting("playwright-cdn"))

# GitHub 发行件下载按序轮询配置镜像，官方地址兜底
GITHUB_MIRRORS = tuple(tool_setting("github-mirrors"))

UV_CACHE_DIR = RUNTIME_DIR / str(tool_setting("uv-cache-dir"))

# wheel 存放目录，随包 runtime 下，装完的引擎库落进 site-packages
WHEELS_DIR = RUNTIME_DIR / "wheels"


def find_uv() -> Path | None:
    """定位可用 uv 可执行文件

    - 依次查找嵌入式运行目录、虚拟环境目录与系统搜索路径
    - 全部找不到返回 None，装库降级为打印手动命令
    """
    exe = RUNTIME_DIR / _UV_EXE_NAME
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
PIP_FLAGS = ["--python", python_target(), "--cache-dir", str(UV_CACHE_DIR)]


def dev_mode() -> bool:
    """判断是否开发模式

    - 找不到任何 uv 即降级，装库只打印手动命令
    """
    return find_uv() is None


def uv_cmd(pip_args: str) -> str:
    """生成开发模式下供手动执行的 uv 命令"""
    return f"uv {pip_args}"


def py_cmd(args: list[str]) -> str:
    """生成开发模式下供手动执行的 python -m 命令

    - 解释器路径写作 python，可直接粘贴进终端执行
    """
    return " ".join(["python", *args[1:]])
