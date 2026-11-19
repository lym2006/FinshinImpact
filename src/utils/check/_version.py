"""版本比对

- 从 GitHub release 列表取各版正文
- 最新一版标签与本地版本比对
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, NoReturn, cast

from exceptions import (
    HTTPStatusError,
    LocalVersionError,
    NetworkError,
    NewVersionError,
    RemoteVersionError,
    describe_error,
)
from skin.messages import VersionMessage
from system.links import RELEASES_PAGE_PATH
from system.tool_settings import declaration
from system.versions import is_upgrade

from ..network import GitClient

_TIMEOUT_RELEASE = 10.0  # release 正文读取超时 10 秒

# release 标签前缀
_TAG_PREFIX = "v"

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
        data = declaration()
        if not data:
            raise LocalVersionError(VersionMessage.LOCAL_MISS) from None
        project = data.get("project")
        local_version = project.get("version") if isinstance(project, dict) else None
        if not isinstance(local_version, str) or not local_version:
            raise LocalVersionError(VersionMessage.LOCAL_BROKEN) from None
        return local_version
    except Exception as e:
        raise LocalVersionError(VersionMessage.LOCAL_BROKEN) from e


async def _fetch(path: str, timeout: float) -> Any | NoReturn:
    """读取远程内容指定路径"""
    try:
        return await GitClient.get_api(path, timeout)
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
                RELEASES_PAGE_PATH.format(size=_RELEASE_PAGE_SIZE, page=page),
                _TIMEOUT_RELEASE,
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


def check_latest(notes: Sequence[ReleaseNote]) -> str | NoReturn:
    """最新一版是否比本机新

    - 取最新一条标签去掉前缀与本地版本比对
    - 读不懂的版本串按远程内容损坏报错
    """
    local_version = _get_local_version()
    remote_version = notes[0].tag.removeprefix(_TAG_PREFIX)

    newer = is_upgrade(local_version, remote_version)
    if newer is None:
        raise RemoteVersionError(VersionMessage.REMOTE_BROKEN)
    if newer:
        raise NewVersionError(local_version, remote_version)

    return local_version
