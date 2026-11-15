"""wheel 取件与指纹核验

- 镜像按序优先、官方直链兜底，代理地址原样递下去
- 同名同指纹的本地件在场即不再取
- 先落 .part 再改名，半截件不留盘
- 每个源的坏法各记一句，合进一条点名到发行件的说明
"""

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


@dataclass(frozen=True, slots=True)
class DownloadOutcome:
    """一只发行件的取件结果

    - path 在场即指纹已核过
    - note 交出即这一步坏了，正文点名到哪只发行件
    """

    distribution: str
    path: Path | None
    note: str


def _file_name_of(url: str) -> str:
    """取直链末段的 wheel 文件名，形态不对交出空串"""
    name = PurePosixPath(urlsplit(url).path).name
    if not name.endswith(_WHEEL_SUFFIX) or "\\" in name:
        return ""
    return name


def _sources(url: str, mirrors: Sequence[str]) -> list[str]:
    """按镜像优先、官方直链兜底排出取件源"""
    return [f"{mirror}{url}" for mirror in mirrors] + [url]


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
    name = _file_name_of(row.url)
    if not name:
        return _reject(row.distribution, CatalogMessage.BAD_FILE_NAME)

    target = target_dir / name
    if target.is_file() and file_digest(target) == row.sha256:
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
        return DownloadOutcome(row.distribution, target, "")

    return _reject(row.distribution, "、".join(steps))
