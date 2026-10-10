# src/utils/version_checker.py
"""版本检查

- 实现本地与远程版本比对
- 提供升级检测与失败回调
"""

import tomllib
from typing import NoReturn, cast

from packaging.version import Version

from exceptions import (
    MAP_KEY_NETWORK,
    MAPS,
    LocalVersionError,
    NetworkError,
    NewVersionError,
    RemoteVersionError,
)
from messages import VersionMessage
from profile_env import ROOT_DIR

from .base_client import BaseClient

_BASE_URL = "https://lym2006.github.io"
_REQUEST_PATH = "/FinshinImpact/pyproject.toml"
_HEADER = {"User-Agent": "Python-Script"}

# 静态小文件读取快，超时从严，失败即报，不做重试拖满等待
_TIMEOUT = 3.0
_CONNECT_TIMEOUT = 2.0


def _get_local_version() -> str | NoReturn:
    """读取本地版本号"""
    try:
        pyproject_path = ROOT_DIR / "pyproject.toml"
        if not pyproject_path.exists():
            raise LocalVersionError(VersionMessage.LOCAL_MISS) from None
        with open(pyproject_path, "rb") as f:
            content = tomllib.load(f)
        local_version = content["project"]["version"]
        return local_version
    except Exception as e:
        raise LocalVersionError(VersionMessage.LOCAL_BROKEN) from e


async def _get_remote_version() -> str | NoReturn:
    """读取远程版本号"""
    try:
        text = await BaseClient.get_content(
            method="text",
            base_url=_BASE_URL,
            request_path=_REQUEST_PATH,
            headers=_HEADER,
            timeout=_TIMEOUT,
            connect_timeout=_CONNECT_TIMEOUT,
            max_retries=1,
        )
        data = tomllib.loads(cast(str, text))
        return data["project"]["version"]
    except NetworkError as e:
        raise RemoteVersionError(MAPS[MAP_KEY_NETWORK][type(e)].format(**vars(e))) from e
    except Exception as e:
        raise RemoteVersionError(VersionMessage.REMOTE_BROKEN) from e


async def check_updates() -> str | NoReturn:
    """检查是否为最新版本"""
    local_version = _get_local_version()
    remote_version = await _get_remote_version()

    if Version(local_version) < Version(remote_version):
        raise NewVersionError(local_version, remote_version)

    return local_version
