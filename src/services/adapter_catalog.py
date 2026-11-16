"""适配器在线目录读取

- 拉 Pages 上生成的适配器目录文本并逐行验字段
- 平台码只认表里写的那一值，认不出的整行不进表
- 行内嵌的版本清单逐条验形态，坏条目只丢那一条
- 坏行与坏段收成说明列表交出
"""

import tomllib
from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Any

from finshin_sdk.domain import Platform
from skin.messages import CatalogMessage
from system.links import CATALOG_PATH, HTTPS_SCHEME
from utils.network import GitClient

_TIMEOUT = 5.0  # 目录读取超时 5 秒
_SHA256_LENGTH = 64  # 指纹串的十六进制字符数
_HEX_DIGITS = frozenset("0123456789abcdef")

# 目录里的段名，与生成侧同值，两处改名必须同步
_SECTION_SDK = "sdk"
_SECTION_ADAPTER = "adapter"


class _RowKey(StrEnum):
    """目录行键位，值即目录里的键名"""

    PLATFORM = "platform"
    DISTRIBUTION = "distribution"
    VERSION = "version"
    URL = "url"
    SHA256 = "sha256"
    VERSIONS = "versions"


# 逐段与逐条验形态时各要看的键位
_RELEASE_KEYS = (_RowKey.DISTRIBUTION, _RowKey.VERSION, _RowKey.URL, _RowKey.SHA256)
_ADAPTER_KEYS = (_RowKey.PLATFORM, *_RELEASE_KEYS)
_VERSION_KEYS = (_RowKey.VERSION, _RowKey.URL, _RowKey.SHA256)


@dataclass(frozen=True, slots=True)
class ReleaseRow:
    """目录里的一只发行件

    - url 是独立整串，不由分发名拼出
    - sha256 归一成小写十六进制串
    - versions 是可装版本清单，最新一版在最前且自身不带清单
    """

    distribution: str
    version: str
    url: str
    sha256: str
    versions: tuple["ReleaseRow", ...] = ()


@dataclass(frozen=True, slots=True)
class Catalog:
    """一份在线目录

    - adapters 按平台码归表，同码只留先读到的那行
    - rejects 逐条点名坏掉的那只发行件与坏的那一步
    """

    sdk: ReleaseRow | None
    adapters: dict[Platform, ReleaseRow]
    rejects: tuple[str, ...]


def _text_of(values: dict[str, Any], key: _RowKey) -> str:
    """取字段文本值，非字符串与空串交出空值"""
    raw = values.get(key)
    return raw if isinstance(raw, str) and raw.strip() else ""


def _is_sha(text: str) -> bool:
    """判指纹串的形态"""
    return len(text) == _SHA256_LENGTH and all(ch in _HEX_DIGITS for ch in text.lower())


def _row_note(values: dict[str, Any], keys: tuple[_RowKey, ...]) -> str:
    """交出一行的拒收说明，字段全合形态即交出空串"""
    name = _text_of(values, _RowKey.DISTRIBUTION) or CatalogMessage.NO_NAME
    for key in keys:
        if not _text_of(values, key):
            return CatalogMessage.ITEM_REJECTED.format(
                name=name, reason=CatalogMessage.MISS_FIELD.format(field=str(key))
            )

    if not _is_sha(_text_of(values, _RowKey.SHA256)):
        reason = CatalogMessage.BAD_SHA
    elif not _text_of(values, _RowKey.URL).startswith(HTTPS_SCHEME):
        reason = CatalogMessage.BAD_URL
    else:
        return ""

    return CatalogMessage.ITEM_REJECTED.format(name=name, reason=reason)


def _build_row(values: dict[str, Any]) -> ReleaseRow:
    """按已验过的字段拼发行件，行内版本清单一并带上"""
    newest = ReleaseRow(
        distribution=_text_of(values, _RowKey.DISTRIBUTION),
        version=_text_of(values, _RowKey.VERSION),
        url=_text_of(values, _RowKey.URL),
        sha256=_text_of(values, _RowKey.SHA256).lower(),
    )

    return replace(newest, versions=(newest, *_older_rows(values, newest)))


def _older_rows(values: dict[str, Any], newest: ReleaseRow) -> tuple[ReleaseRow, ...]:
    """行内的旧版条目，形态不合或版本号与已有的重复即只丢那一条"""
    listed = values.get(_RowKey.VERSIONS)
    if not isinstance(listed, list):
        return ()

    older: list[ReleaseRow] = []
    seen = {newest.version}
    for item in listed:
        row = _version_row(item, newest.distribution)
        if row is None or row.version in seen:
            continue
        seen.add(row.version)
        older.append(row)

    return tuple(older)


def _version_row(item: Any, distribution: str) -> ReleaseRow | None:
    """一条旧版条目，字段或形态不合即不交出"""
    if not isinstance(item, dict) or _row_note(item, _VERSION_KEYS):
        return None

    return ReleaseRow(
        distribution=distribution,
        version=_text_of(item, _RowKey.VERSION),
        url=_text_of(item, _RowKey.URL),
        sha256=_text_of(item, _RowKey.SHA256).lower(),
    )


def _platform_of(raw: Any) -> Platform | None:
    """认平台码"""
    if not isinstance(raw, str):
        return None
    try:
        return Platform(raw)
    except ValueError:
        return None


def _read_sdk(data: dict[str, Any]) -> tuple[ReleaseRow | None, list[str]]:
    """读接口包那一段"""
    values = data.get(_SECTION_SDK)
    if not isinstance(values, dict):
        return None, [CatalogMessage.SDK_MISSING]
    note = _row_note(values, _RELEASE_KEYS)
    if note:
        return None, [note]

    return _build_row(values), []


def _read_adapters(
    data: dict[str, Any],
) -> tuple[dict[Platform, ReleaseRow], list[str]]:
    """逐行读适配器条目，交出按平台码归的表与拒收说明"""
    rows = data.get(_SECTION_ADAPTER)
    if not isinstance(rows, list):
        return {}, []

    table: dict[Platform, ReleaseRow] = {}
    notes: list[str] = []
    for values in rows:
        if not isinstance(values, dict):
            notes.append(CatalogMessage.NOT_A_ROW)
            continue
        note = _row_note(values, _ADAPTER_KEYS)
        if note:
            notes.append(note)
            continue
        platform = _platform_of(values.get(_RowKey.PLATFORM))
        if platform is None:
            notes.append(
                CatalogMessage.PLATFORM_UNKNOWN.format(
                    code=_text_of(values, _RowKey.PLATFORM)
                )
            )
            continue
        if platform in table:
            notes.append(CatalogMessage.PLATFORM_DUP.format(code=str(platform)))
            continue
        table[platform] = _build_row(values)

    return table, notes


def _parse(text: str) -> Catalog:
    """解析目录文本

    - 文本不是 TOML 时整份判坏，只交出一条说明
    """
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return Catalog(None, {}, (CatalogMessage.BROKEN,))

    sdk, sdk_notes = _read_sdk(data)
    adapters, row_notes = _read_adapters(data)

    return Catalog(sdk, adapters, (*sdk_notes, *row_notes))


async def load_catalog(proxy: str | None = None) -> Catalog:
    """读取在线目录

    - 一次请求取文本，字段逐行验
    - 交出代理地址即走代理取
    """
    text = await GitClient.get_pages(CATALOG_PATH, _TIMEOUT, proxy)

    return _parse(text)
