# src/bootstrap/_plugin/_env.py
"""装库环境定位

- 定位嵌入式解释器与 uv 可执行文件
- 读 pyproject 工具表作换源序列与缓存目录的单源
"""

import shutil
import sys
import tomllib
from pathlib import Path
from typing import Any

from profile_env import ROOT_DIR

PYPROJECT = ROOT_DIR / "pyproject.toml"

RUNTIME_DIR = ROOT_DIR / "runtime"
_PY_EXE = RUNTIME_DIR / "python.exe"

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
    """
    if key not in _SETTINGS:
        # 代码兜底默认值会造出第二份不一致副本
        raise RuntimeError(f"pyproject 缺 [tool.finshin-impact].{key}")
    return _SETTINGS[key]


# uv 索引按序重试：国内多源轮询，最后官方源兜底
UV_INDEX_URLS = tuple(_require("uv-index-urls"))

# 内核下载走配置镜像，失败清变量回退官方源
PLAYWRIGHT_CDN = str(_require("playwright-cdn"))

UV_CACHE_DIR = RUNTIME_DIR / str(_require("uv-cache-dir"))


def find_uv() -> Path | None:
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
