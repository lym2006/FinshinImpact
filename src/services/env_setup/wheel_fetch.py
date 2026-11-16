"""wheel 取件与指纹核验

- 镜像按序优先、官方直链兜底，代理地址原样递下去
- 目录行对应的件已在盘上且指纹对得上即不重取
- 核过指纹的件把指纹留在同目录一份索引里，目录取不到时仍认得这份件
- 按发行件名盘点什么件已在这台机器上，不读内容
- 先落 .part 再改名，半截件不留盘
- 每个源的坏法各记一句，合进一条点名到发行件的说明
"""

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

from exceptions import NetworkError
from skin.messages import CatalogMessage
from system.digest import file_digest
from utils.network import GitClient

from ..adapter_catalog import ReleaseRow

# wheel 附件名后缀，与生成侧同值，两处改名必须同步
_WHEEL_SUFFIX = ".whl"
_PART_SUFFIX = ".part"

_TIMEOUT_DOWNLOAD = 120.0  # 单只发行件下载超时 2 分钟
_WHEEL_PARTS = 5  # wheel 文件名的段数，版本是第二段，与目录生成侧同一算法

# 本机指纹索引的文件名，跟着 wheel 同进同出
_INDEX_NAME = "downloaded.json"


@dataclass(frozen=True, slots=True)
class DownloadOutcome:
    """一只发行件的取件结果

    - path 在场即指纹已核过
    - note 交出即这一步坏了，正文点名到哪只发行件
    """

    distribution: str
    path: Path | None
    note: str


def file_name_of(url: str) -> str:
    """取直链末段的 wheel 文件名，形态不对交出空串"""
    name = PurePosixPath(urlsplit(url).path).name
    if not name.endswith(_WHEEL_SUFFIX) or "\\" in name:
        return ""
    return name


def _version_in_name(name: str) -> str:
    """取 wheel 文件名第二段版本号，段数不对交出空串"""
    parts = name.split("-")
    return parts[1] if len(parts) >= _WHEEL_PARTS else ""


def _recorded_digests(target_dir: Path) -> dict[str, str]:
    """本机记过的件与指纹，索引不在场或读不出即空"""
    path = target_dir / _INDEX_NAME
    if not path.is_file():
        return {}
    try:
        table = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(table, dict):
        return {}

    return {
        name: value
        for name, value in table.items()
        if isinstance(name, str) and isinstance(value, str)
    }


def _record_digest(target_dir: Path, name: str, sha256: str) -> bool:
    """把核过的指纹记进本机索引，写不进即不记，读数按没记处理"""
    table = _recorded_digests(target_dir)
    table[name] = sha256
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / _INDEX_NAME).write_text(
            json.dumps(table, sort_keys=True, indent=1) + "\n", encoding="utf-8"
        )
    except OSError:
        return False

    return True


def local_release(distribution: str, name: str, target_dir: Path) -> ReleaseRow | None:
    """本机记过指纹的那份件拼成一行可装目标，没记或读不出版本即不交出

    - 盘上那份件与记下的指纹不符即不算
    """
    sha256 = _recorded_digests(target_dir).get(name, "")
    version = _version_in_name(name)
    target = target_dir / name
    if not sha256 or not version or not target.is_file():
        return None
    if file_digest(target) != sha256:
        return None

    return ReleaseRow(
        distribution=distribution,
        version=version,
        url=target.as_uri(),
        sha256=sha256,
    )


def _sources(url: str, mirrors: Sequence[str]) -> list[str]:
    """按镜像优先、官方直链兜底排出取件源"""
    return [f"{mirror}{url}" for mirror in mirrors] + [url]


def is_cached(row: ReleaseRow, target_dir: Path) -> bool:
    """目录行对应的那份件已在盘上且指纹对得上"""
    name = file_name_of(row.url)
    if not name:
        return False
    target = target_dir / name

    return target.is_file() and file_digest(target) == row.sha256


def disk_files(distribution: str, target_dir: Path) -> tuple[str, ...]:
    """盘上属于这只发行件的 wheel 文件名，按名升序，目录不在场即空

    - 下载没跑完的 .part 不算一份件
    """
    if not target_dir.is_dir():
        return ()
    stem = f"{distribution.replace('-', '_')}-"

    return tuple(
        sorted(
            item.name
            for item in target_dir.iterdir()
            if item.is_file()
            and item.name.startswith(stem)
            and item.name.endswith(_WHEEL_SUFFIX)
        )
    )


def _reject(distribution: str, reason: str) -> DownloadOutcome:
    """拼一条点名到发行件的拒收结果"""
    return DownloadOutcome(
        distribution,
        None,
        CatalogMessage.ITEM_REJECTED.format(name=distribution, reason=reason),
    )


async def download_release(
    row: ReleaseRow,
    target_dir: Path,
    mirrors: Sequence[str],
    proxy: str | None = None,
) -> DownloadOutcome:
    """取一只发行件并核指纹

    - 落盘件与目录指纹不符即删掉那份件并换下一源
    """
    name = file_name_of(row.url)
    if not name:
        return _reject(row.distribution, CatalogMessage.BAD_FILE_NAME)

    target = target_dir / name
    if is_cached(row, target_dir):
        _record_digest(target_dir, name, row.sha256)
        return DownloadOutcome(row.distribution, target, "")

    steps: list[str] = []
    part = target.with_name(target.name + _PART_SUFFIX)
    for source in _sources(row.url, mirrors):
        try:
            body = await GitClient.get_file(source, _TIMEOUT_DOWNLOAD, proxy)
        except NetworkError:
            body = None
        if body is None:
            steps.append(CatalogMessage.FETCH_FAILED.format(url=source))
            continue
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            part.write_bytes(body)
        except OSError:
            steps.append(CatalogMessage.WRITE_FAILED)
            continue
        if file_digest(part) != row.sha256:
            part.unlink(missing_ok=True)
            steps.append(CatalogMessage.SHA_MISMATCH)
            continue
        part.replace(target)
        _record_digest(target_dir, name, row.sha256)
        return DownloadOutcome(row.distribution, target, "")

    return _reject(row.distribution, "、".join(steps))
