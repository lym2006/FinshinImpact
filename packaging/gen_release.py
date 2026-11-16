"""适配器目录的远端取数

- 账号名取检出环境，仓清单与 release 清单按账号下各仓取
- 按默认分支声明里的分发名认接口包与适配器，仓名不参与判定
- 平台码、分发名与版本取自声明，直链与指纹取 release 附件自报的值
- 每只发行件交一行，行内是最新一版，随段带可装的旧版本清单
"""

import base64
import os
import tomllib
from typing import Any

import net_channel
import pack_spec

_TIMEOUT = 20.0  # 单次请求超时 20 秒
_PER_PAGE = 100  # 列仓与列 release 的单页条数
_ACCEPT = "application/vnd.github+json"  # 取件要的响应格式
_VERSIONS_MAX = 10  # 一只发行件进目录的版本条数
_WHEEL_PARTS = 5  # wheel 文件名的段数，版本是第二段

# 分发名口径与开发工具清单里那两条一致，改名要一起改
SDK_DISTRIBUTION = "finshin-sdk"
_ADAPTER_PREFIX = "finshin-adapter-"

# 目录行与版本条目的键位，与本体读目录那侧同值，两处改名必须同步
KEY_PLATFORM = "platform"
KEY_DISTRIBUTION = "distribution"
KEY_VERSION = "version"
KEY_URL = "url"
KEY_SHA256 = "sha256"
KEY_VERSIONS = "versions"

# 一条版本条目的键序
VERSION_KEYS = (KEY_VERSION, KEY_URL, KEY_SHA256)

# 声明里的项目段与键名，与各仓那份 pyproject 同值
_DECL_PROJECT = "project"
_DECL_TOOL = "tool"
_DECL_NAME = "name"
_DECL_FILE = pack_spec.PackLayout.DECLARATION
_DECL_ADAPTER_TABLE = "finshin-adapter"

_WHEEL_SUFFIX = ".whl"
_DIGEST_SEP = ":"


def owner() -> str:
    """取仓库所属账号"""
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    name, slash, _ = repo.partition("/")
    if not slash or not name:
        raise RuntimeError("GITHUB_REPOSITORY 没给出账号名")
    return name


def _headers() -> dict[str, str]:
    """拼请求头"""
    table = {pack_spec.HDR_USER_AGENT: "finshin-catalog", "Accept": _ACCEPT}
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        table[pack_spec.HDR_AUTHORIZATION] = f"Bearer {token}"
    return table


def _get(url: str) -> Any:
    """按干净通道取一份 JSON，重发次数用完交出 None"""
    return net_channel.fetch_json(url, net_channel.openers(), _headers(), _TIMEOUT)


def repos(account: str) -> list[dict[str, Any]]:
    """列出账号下未归档的仓"""
    data = _get(f"{pack_spec.API_HOST}/users/{account}/repos?per_page={_PER_PAGE}")
    if not isinstance(data, list):
        raise RuntimeError(f"取不到账号 {account} 的仓清单")

    rows = [row for row in data if isinstance(row, dict) and not row.get("archived")]
    return [row for row in rows if isinstance(row.get("default_branch"), str)]


def _release(name: str) -> dict[str, Any] | None:
    """取指定仓的最新 release"""
    data = _get(f"{pack_spec.API_HOST}/repos/{name}/releases/latest")
    return data if isinstance(data, dict) else None


def _releases(name: str) -> list[dict[str, Any]]:
    """列指定仓的 release，草稿与预发布不进目录"""
    data = _get(f"{pack_spec.API_HOST}/repos/{name}/releases?per_page={_PER_PAGE}")
    if not isinstance(data, list):
        return []

    return [
        item
        for item in data
        if isinstance(item, dict)
        and not item.get("draft")
        and not item.get("prerelease")
    ]


def _declaration(name: str, ref: str) -> dict[str, Any] | None:
    """取指定仓某个检出点的声明

    - 走 contents 口，与 release 同一个 host
    """
    data = _get(f"{pack_spec.API_HOST}/repos/{name}/contents/{_DECL_FILE}?ref={ref}")
    body = data.get("content") if isinstance(data, dict) else None
    if not isinstance(body, str):
        return None
    try:
        return tomllib.loads(base64.b64decode(body).decode("utf-8"))
    except (ValueError, tomllib.TOMLDecodeError):
        return None


def _project_value(data: dict[str, Any] | None, key: str) -> str:
    """取声明项目段里的文本值"""
    project = (data or {}).get(_DECL_PROJECT)
    value = project.get(key) if isinstance(project, dict) else None
    return value if isinstance(value, str) else ""


def _platform_of(data: dict[str, Any] | None) -> str:
    """取声明里自报的平台码"""
    tool = (data or {}).get(_DECL_TOOL)
    table = tool.get(_DECL_ADAPTER_TABLE) if isinstance(tool, dict) else None
    code = table.get(KEY_PLATFORM) if isinstance(table, dict) else None
    return code if isinstance(code, str) else ""


def _wheel_of(release: dict[str, Any], distribution: str) -> tuple[str, str, str]:
    """取 release 里属于这只分发名的 wheel 文件名、直链与指纹

    - 直链整串取附件自己报的地址
    - 指纹取附件的 digest，算法名不是 sha256 即不算
    """
    stem = distribution.replace("-", "_")
    for asset in release.get("assets") or []:
        name = str(asset.get("name") or "") if isinstance(asset, dict) else ""
        if not name.startswith(f"{stem}-") or not name.endswith(_WHEEL_SUFFIX):
            continue
        url = str(asset.get("browser_download_url") or "")
        scheme, sep, value = str(asset.get("digest") or "").partition(_DIGEST_SEP)
        if url and sep and scheme == KEY_SHA256:
            return name, url, value

    return "", "", ""


def _version_in_name(name: str) -> str:
    """取 wheel 文件名第二段版本号，段数不对交出空串"""
    parts = name.split("-")
    return parts[1] if len(parts) >= _WHEEL_PARTS else ""


def _versions(
    name: str, distribution: str, newest_tag: str, newest: dict[str, Any]
) -> list[dict[str, Any]]:
    """排出一只发行件的可装版本清单，最新那一版在最前

    - 旧版的版本号取 wheel 文件名，不回读那一版的声明
    - 旧版缺直链、指纹或文件名读不出版本号的只丢那一版
    """
    listed: list[dict[str, Any]] = [{key: newest[key] for key in VERSION_KEYS}]
    seen = {str(newest[KEY_VERSION])}
    for release in _releases(name):
        if len(listed) >= _VERSIONS_MAX:
            break
        if str(release.get("tag_name") or "") == newest_tag:
            continue
        older = _older_row(distribution, release)
        if older is None or older[KEY_VERSION] in seen:
            continue
        seen.add(str(older[KEY_VERSION]))
        listed.append(older)

    return listed


def _older_row(distribution: str, release: dict[str, Any]) -> dict[str, Any] | None:
    """一版旧件的可装条目，文件名读不出版本号即不交出"""
    asset, url, sha256 = _wheel_of(release, distribution)
    version = _version_in_name(asset)
    if not version:
        return None

    return {KEY_VERSION: version, KEY_URL: url, KEY_SHA256: sha256}


def release_row(name: str, ref: str) -> tuple[dict[str, Any] | None, str]:
    """读一只仓的发行件与可装版本清单，交出行或跳过原因

    - 默认分支声明里的分发名不属这一族即跳过
    - 属这一族却没发版即跳过，那是发布者自己的事
    - 最新那一版缺声明、wheel 直链、指纹或平台码的，当场报错
    """
    distribution = _project_value(_declaration(name, ref), _DECL_NAME)
    if distribution != SDK_DISTRIBUTION and not distribution.startswith(
        _ADAPTER_PREFIX
    ):
        return None, f"{name}：分发名 {distribution or '未写'} 不属本体这一族"

    release = _release(name)
    if release is None:
        return None, f"{name}：{distribution} 还没 release"

    tag = str(release.get("tag_name") or "")
    data = _declaration(name, tag)
    if data is None:
        raise RuntimeError(f"{name}：{tag} 的声明读不出")
    if _project_value(data, _DECL_NAME) != distribution:
        raise RuntimeError(f"{name}：{tag} 的分发名与默认分支不一致")

    version = _project_value(data, KEY_VERSION)
    _, url, sha256 = _wheel_of(release, distribution)
    if not url or not sha256 or not version:
        raise RuntimeError(f"{name}：{tag} 缺 wheel 直链、指纹或版本号")

    row: dict[str, Any] = {
        KEY_DISTRIBUTION: distribution,
        KEY_VERSION: version,
        KEY_URL: url,
        KEY_SHA256: sha256,
    }
    if distribution != SDK_DISTRIBUTION:
        code = _platform_of(data)
        if not code:
            raise RuntimeError(f"{name}：{tag} 的声明里没写平台码")
        row[KEY_PLATFORM] = code

    row[KEY_VERSIONS] = _versions(name, distribution, tag, row)

    return row, ""
