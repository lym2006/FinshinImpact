# src/utils/check/_version.py
"""版本检查

- 本地与远程版本比对
- 升级检测与失败回调
- 从 GitHub release 正文取版本变化内容
"""

import asyncio
import re
import tomllib
from dataclasses import dataclass
from typing import Any, Literal, NoReturn, cast

from packaging.version import Version

from exceptions import (
    ConnectionFailedError,
    HTTPStatusError,
    LocalVersionError,
    NetworkError,
    NewVersionError,
    RemoteVersionError,
    RequestTimeoutError,
    describe_error,
)
from skin.messages import VersionMessage
from system.profile_env import ROOT_DIR

from ..network import BaseClient

_PAGES_BASE_URL = "https://lym2006.github.io"
_PYPROJECT_PATH = "/FinshinImpact/pyproject.toml"
_RELEASE_BASE_URL = "https://api.github.com"
_RELEASE_PATH = "/repos/lym2006/FinshinImpact/releases?per_page={size}&page={page}"
_HEADER = {"User-Agent": "Python-Script"}

# 建连失败与超时重发一次即止，不拖满等待
_TIMEOUT = 3.0  # 版本页读取超时 3 秒
_CONNECT_TIMEOUT = 2.0  # 建连超时 2 秒
_TIMEOUT_RELEASE = 10.0  # release 正文读取超时 10 秒

# 未认证 API 单页最多 100 条，多出的量换页取
_RELEASE_PAGE_SIZE = 100

# 翻页收口保护，短页即到底，正常到不了这一页
_RELEASE_MAX_PAGES = 10

_DOWNLOAD_MARK = "releases/download/"  # 发布包直链所在行的标记

# 裸链接会在版本号的小数点处被截断，只剩前半段可点
_BARE_URL = re.compile(r"(?<![(<])(https?://\S+)")


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


class _VersionClient(BaseClient):
    """版本页与 release 接口的取件客户端

    - 建连失败或超时等一秒重发一次，两次都坏才上抛
    """

    _RETRY_DELAY = 1.0  # 重发前的等待秒数

    @classmethod
    async def _once(
        cls,
        method: Literal["json", "text"],
        base_url: str,
        request_path: str,
        headers: dict[str, Any] | None,
        timeout: float,
    ) -> dict[str, Any] | str | None:
        """取一份内容，异常原样上抛"""
        return await cls.get_content(
            method=method,
            base_url=base_url,
            request_path=request_path,
            headers=headers,
            timeout=timeout,
            connect_timeout=_CONNECT_TIMEOUT,
        )

    @classmethod
    async def fetch(
        cls,
        method: Literal["json", "text"],
        base_url: str,
        request_path: str,
        headers: dict[str, Any] | None,
        timeout: float,
    ) -> dict[str, Any] | str | None:
        """取一份内容，建连失败或超时重发一次"""
        try:
            return await cls._once(method, base_url, request_path, headers, timeout)
        except (ConnectionFailedError, RequestTimeoutError):
            await asyncio.sleep(cls._RETRY_DELAY)
            return await cls._once(method, base_url, request_path, headers, timeout)


async def _fetch(
    path: str,
    timeout: float,
    *,
    base_url: str = _PAGES_BASE_URL,
    method: Literal["json", "text"] = "text",
) -> dict[str, Any] | str | NoReturn:
    """读取远程内容指定路径"""
    try:
        content = await _VersionClient.fetch(
            method=method,
            base_url=base_url,
            request_path=path,
            headers=_HEADER,
            timeout=timeout,
        )
        return cast(dict[str, Any], content)
    except HTTPStatusError as e:
        raise RemoteVersionError(describe_error(e)) from e
    except NetworkError as e:
        raise RemoteVersionError(describe_error(e)) from e
    except Exception as e:
        raise RemoteVersionError(VersionMessage.REMOTE_BROKEN) from e


def _drop_download_lines(body: str) -> str:
    """release 正文剔掉发布包直链所在行"""
    return "\n".join(
        line for line in body.splitlines() if _DOWNLOAD_MARK not in line
    ).strip()


def _autolink_bare_urls(body: str) -> str:
    """release 正文的裸链接改写为尖括号自动链接"""
    return _BARE_URL.sub(r"<\1>", body)


async def _get_remote_version() -> str | NoReturn:
    """读取远程版本号"""
    text = cast(str, await _fetch(_PYPROJECT_PATH, _TIMEOUT))
    try:
        data = tomllib.loads(text)
        return data["project"]["version"]
    except Exception as e:
        raise RemoteVersionError(VersionMessage.REMOTE_BROKEN) from e


async def check_updates() -> str | NoReturn:
    """检查是否为最新版本"""
    local_version = _get_local_version()
    remote_version = await _get_remote_version()

    if Version(local_version) < Version(remote_version):
        raise NewVersionError(local_version, remote_version)

    return local_version


@dataclass(frozen=True)
class ReleaseNote:
    """单版发布说明

    - body 已剔掉发布包直链行，裸链接补成尖括号
    """

    tag: str
    body: str


def _to_note(row: dict[str, Any]) -> ReleaseNote:
    """release 条目转发布说明"""
    return ReleaseNote(
        tag=str(row.get("tag_name") or ""),
        body=_autolink_bare_urls(_drop_download_lines(str(row.get("body") or ""))),
    )


async def release_history() -> tuple[ReleaseNote, ...] | NoReturn:
    """按页拉取全部版本的发布说明

    - 新在前，短页即到底
    """
    notes: list[ReleaseNote] = []
    for page in range(1, _RELEASE_MAX_PAGES + 1):
        rows = cast(
            Any,
            await _fetch(
                _RELEASE_PATH.format(size=_RELEASE_PAGE_SIZE, page=page),
                _TIMEOUT_RELEASE,
                base_url=_RELEASE_BASE_URL,
                method="json",
            ),
        )
        if not isinstance(rows, list):
            raise RemoteVersionError(VersionMessage.REMOTE_BROKEN)

        notes.extend(_to_note(row) for row in rows if isinstance(row, dict))
        if len(rows) < _RELEASE_PAGE_SIZE:
            break

    if not notes:
        raise RemoteVersionError(VersionMessage.REMOTE_BROKEN)

    return tuple(notes)
