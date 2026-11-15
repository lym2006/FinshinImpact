"""适配器在线目录生成

- 按默认分支声明里的分发名认接口包与适配器，仓名不参与判定
- 平台码、分发名与版本取自该版声明
- 下载直链与指纹整串取 release 附件自己报的值
- 已发版却取不到声明、wheel 或指纹的仓当场报错，不出半截目录
"""

import base64
import json
import os
import sys
import tomllib
from typing import Any

import net_channel
import pack_spec

_TIMEOUT = 20.0  # 单次请求超时 20 秒
_PER_PAGE = 100  # 列仓单页条数
_ACCEPT = "application/vnd.github+json"  # 取件要的响应格式

# 分发名口径与开发工具清单里那两条一致，改名要一起改
_SDK_DISTRIBUTION = "finshin-sdk"
_ADAPTER_PREFIX = "finshin-adapter-"

# 目录里的段名与键位，与本体读目录那侧同值，两处改名必须同步
_SECTION_SDK = "sdk"
_SECTION_ADAPTER = "adapter"
_KEY_PLATFORM = "platform"
_KEY_DISTRIBUTION = "distribution"
_KEY_VERSION = "version"
_KEY_URL = "url"
_KEY_SHA256 = "sha256"

_SDK_ORDER = (_KEY_DISTRIBUTION, _KEY_VERSION, _KEY_URL, _KEY_SHA256)
_ADAPTER_ORDER = (_KEY_PLATFORM, *_SDK_ORDER)

# 声明里的项目段与键名，与各仓那份 pyproject 同值
_DECL_PROJECT = "project"
_DECL_TOOL = "tool"
_DECL_NAME = "name"
_DECL_FILE = pack_spec.PackLayout.DECLARATION
_DECL_ADAPTER_TABLE = "finshin-adapter"

_WHEEL_SUFFIX = ".whl"
_DIGEST_SEP = ":"


def _owner() -> str:
    """取仓库所属账号"""
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    owner, slash, _ = repo.partition("/")
    if not slash or not owner:
        raise RuntimeError("GITHUB_REPOSITORY 没给出账号名")
    return owner


def _headers() -> dict[str, str]:
    """拼请求头"""
    headers = {pack_spec.HDR_USER_AGENT: "finshin-catalog", "Accept": _ACCEPT}
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        headers[pack_spec.HDR_AUTHORIZATION] = f"Bearer {token}"
    return headers


def _get(url: str) -> Any:
    """按干净通道取一份 JSON，重发次数用完交出 None"""
    return net_channel.fetch_json(url, net_channel.clean_opener(), _headers(), _TIMEOUT)


def _repos(owner: str) -> list[dict[str, Any]]:
    """列出账号下未归档的仓"""
    data = _get(f"{pack_spec.API_HOST}/users/{owner}/repos?per_page={_PER_PAGE}")
    if not isinstance(data, list):
        raise RuntimeError(f"取不到账号 {owner} 的仓清单")

    rows = [row for row in data if isinstance(row, dict) and not row.get("archived")]
    return [row for row in rows if isinstance(row.get("default_branch"), str)]


def _release(name: str) -> dict[str, Any] | None:
    """取指定仓的最新 release"""
    data = _get(f"{pack_spec.API_HOST}/repos/{name}/releases/latest")
    return data if isinstance(data, dict) else None


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
    code = table.get(_KEY_PLATFORM) if isinstance(table, dict) else None
    return code if isinstance(code, str) else ""


def _wheel_of(release: dict[str, Any], distribution: str) -> tuple[str, str]:
    """取 release 里属于这只分发名的 wheel 直链与指纹

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
        if url and sep and scheme == _KEY_SHA256:
            return url, value

    return "", ""


def _row(name: str, ref: str) -> tuple[dict[str, Any] | None, str]:
    """读一只仓的发行件，交出行或跳过原因

    - 默认分支声明里的分发名不属这一族即跳过
    - 属这一族却没发版即跳过，那是发布者自己的事
    - 发了版却缺声明、wheel 直链、指纹或平台码的，当场报错
    """
    distribution = _project_value(_declaration(name, ref), _DECL_NAME)
    if distribution != _SDK_DISTRIBUTION and not distribution.startswith(
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

    version = _project_value(data, _KEY_VERSION)
    url, sha256 = _wheel_of(release, distribution)
    if not url or not sha256 or not version:
        raise RuntimeError(f"{name}：{tag} 缺 wheel 直链、指纹或版本号")

    row = {
        _KEY_DISTRIBUTION: distribution,
        _KEY_VERSION: version,
        _KEY_URL: url,
        _KEY_SHA256: sha256,
    }
    if distribution != _SDK_DISTRIBUTION:
        code = _platform_of(data)
        if not code:
            raise RuntimeError(f"{name}：{tag} 的声明里没写平台码")
        row[_KEY_PLATFORM] = code

    return row, ""


def _lines(row: dict[str, Any], order: tuple[str, ...]) -> list[str]:
    """按固定键序把一行写成键值串"""
    return [f"{key} = {json.dumps(row[key])}" for key in order if key in row]


def _dump(sdk: dict[str, Any], adapters: list[dict[str, Any]]) -> str:
    """把目录写成 TOML 文本"""
    blocks = [f"[{_SECTION_SDK}]", *_lines(sdk, _SDK_ORDER)]
    for row in adapters:
        blocks.append("")
        blocks.append(f"[[{_SECTION_ADAPTER}]]")
        blocks.extend(_lines(row, _ADAPTER_ORDER))

    return "\n".join(blocks) + "\n"


def _build() -> str:
    """聚合账号下所有属于本体这一族的发行件

    - 接口包一段，适配器按平台码升序逐段
    """
    owner = _owner()
    sdk: dict[str, Any] | None = None
    adapters: list[dict[str, Any]] = []
    for repo in _repos(owner):
        name = str(repo.get("full_name") or "")
        ref = str(repo.get("default_branch") or "")
        row, reason = _row(name, ref)
        if row is None:
            print(f"跳过 {reason}", file=sys.stderr)
            continue
        if _KEY_PLATFORM in row:
            adapters.append(row)
        elif sdk is None:
            sdk = row

    if sdk is None:
        raise RuntimeError(f"账号 {owner} 下取不到 {_SDK_DISTRIBUTION} 的发行件")
    if not adapters:
        raise RuntimeError(f"账号 {owner} 下一只适配器都没取到")

    adapters.sort(key=lambda item: str(item[_KEY_PLATFORM]))

    return _dump(sdk, adapters)


def main() -> None:
    """生成目录并写到指定文件"""
    if len(sys.argv) < 2:
        raise RuntimeError("用法：gen_catalog.py <输出路径>")

    with open(sys.argv[1], "w", encoding="utf-8", newline="\n") as handle:
        handle.write(_build())
    print(f"目录写出：接口包见 {_SECTION_SDK} 段，适配器见 {_SECTION_ADAPTER} 段")


if __name__ == "__main__":
    main()
