# src/utils/_check_version.py
"""版本检查（内部实现）

- 实现本地与远程版本比对
- 提供升级检测与失败回调
"""

import tomllib
from typing import NoReturn, cast

from packaging.version import Version

from exceptions import (
    MAPS,
    LocalVersionError,
    NetworkError,
    NewVersionError,
    RemoteVersionError,
)

from ._base_client import BaseClient
from ._root_dir import ROOT_DIR

_BASE_URL = "https://lym2006.github.io"
_REQUEST_PATH = "/TelegramBot/pyproject.toml"
_HEADER = {"User-Agent": "Python-Script"}

# ==================== 内部辅助函数 ====================


def _get_local_version() -> str | NoReturn:
    """读取本地版本号"""
    try:
        pyproject_path = ROOT_DIR / "pyproject.toml"
        if not pyproject_path.exists():
            raise LocalVersionError("项目文件不存在") from None
        with open(pyproject_path, "rb") as f:
            content = tomllib.load(f)
        local_version = content["project"]["version"]
        return local_version
    except Exception as e:
        raise LocalVersionError("读取失败") from e


async def _get_remote_version() -> str | NoReturn:
    """读取远程版本号"""
    try:
        text = await BaseClient.get_content(
            method="text",
            base_url=_BASE_URL,
            request_path=_REQUEST_PATH,
            headers=_HEADER,
        )
        data = tomllib.loads(cast(str, text))
        return data["project"]["version"]
    except NetworkError as e:
        raise RemoteVersionError(MAPS["Network"][type(e)].format(**vars(e))) from e
    except Exception as e:
        raise RemoteVersionError("读取未知错误") from e


# ==================== 核心版本检查逻辑 ====================


async def check_updates() -> str | NoReturn:
    """检查是否为最新版本"""
    local_version = _get_local_version()
    remote_version = await _get_remote_version()

    if Version(local_version) < Version(remote_version):
        raise NewVersionError(local_version, remote_version)

    return local_version
