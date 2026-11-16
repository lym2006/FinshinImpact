"""平台组件行拼装

- 本机读数并上在线目录行，接口包在最前
- 归属档按本机来路、本机版本与在线版本比出来，版本串读不懂算本机已有
- 来源与发行件名按同一条规则排，接口包与适配器不分两样
"""

from dataclasses import dataclass
from enum import StrEnum

from system.distributions import SDK_DISTRIBUTION, installed_version
from system.profile_env import DECLARATION_FILE_NAME, ROOT_DIR
from system.tool_settings import project_value
from system.versions import is_upgrade

from ..adapter_catalog import Catalog, ReleaseRow
from ..adapter_manifest import (
    InstalledAdapter,
    installed_adapters,
    load_adapter_manifests,
    tree_distributions,
)

# 目录行归表时接口包占的那个空位
_SDK_CODE = ""

# 接口包源码的挂载目录，与 packaging 侧现打 wheel 时取的是同一处
_SDK_TREE_DIR = "finshin/sdk"


class ComponentSource(StrEnum):
    """一只组件在本机的来路

    - TREE_INSTALLED 挂载的源码仓在场，那只包也装进了环境
    - TREE_ONLY 挂载的源码仓在场，环境里没那只包
    - INSTALLED 声明与代码都取环境里那只包
    - NONE 本机没有
    """

    TREE_INSTALLED = "tree_installed"
    TREE_ONLY = "tree_only"
    INSTALLED = "installed"
    NONE = "none"


class ComponentBucket(StrEnum):
    """一只组件在本页归到哪一档

    - LOCAL 本机已有
    - UPGRADABLE 在线比本机新
    - ONLINE 只有在线有
    """

    LOCAL = "local"
    UPGRADABLE = "upgradable"
    ONLINE = "online"


@dataclass(frozen=True, slots=True)
class ComponentRow:
    """一只组件在本页的一行

    - 接口包这行没有平台码，按空串排到最前
    - installed 与 requires 各留各的空串，本机没在场即是空
    - release 在场才有得装，目录行自带直链与指纹
    """

    platform: str
    distribution: str
    source: ComponentSource
    installed: str
    requires: str
    release: ReleaseRow | None
    bucket: ComponentBucket


def component_rows(catalog: Catalog | None) -> tuple[ComponentRow, ...]:
    """本机读数并上在线目录行的完整读数

    - 目录交 None 即只出本机在场的那些
    """
    return _rows(catalog)


def present_platforms() -> frozenset[str]:
    """本机装着适配器包的那些平台码，接口包那行不算平台

    - 源码仓挂着但没装进环境的不算可用，代码取不到
    """
    return frozenset(
        row.platform for row in _rows(None) if row.platform and row.installed
    )


def _rows(catalog: Catalog | None) -> tuple[ComponentRow, ...]:
    """按本机在场件与目录行排出组件行，接口包在最前"""
    installed = _installed_by_platform()
    requires = _declared_requires()
    tree = {str(platform): name for platform, name in tree_distributions().items()}
    releases = _releases_by_code(catalog)
    sdk_name = _sdk_tree_name()
    sdk_version = installed_version(SDK_DISTRIBUTION)
    rows = [
        _row(
            _SDK_CODE,
            sdk_name or SDK_DISTRIBUTION,
            _source_of(bool(sdk_name), bool(sdk_version)),
            sdk_version,
            "",
            releases.get(_SDK_CODE),
        )
    ]

    codes = sorted(
        set(installed) | set(requires) | set(tree) | (set(releases) - {_SDK_CODE})
    )
    for code in codes:
        item = installed.get(code)
        release = releases.get(code)
        rows.append(
            _row(
                code,
                _distribution_name(tree.get(code, ""), item, release),
                _source_of(code in tree, item is not None),
                item.version if item else "",
                requires.get(code, ""),
                release,
            )
        )

    return tuple(rows)


def _sdk_tree_name() -> str:
    """挂载的接口包仓在场即交出它声明的发行件名，不在场交出空串"""
    return project_value("name", ROOT_DIR / _SDK_TREE_DIR / DECLARATION_FILE_NAME)


def _distribution_name(
    tree_name: str, item: InstalledAdapter | None, release: ReleaseRow | None
) -> str:
    """发行件名，挂载仓那份、已装包元数据、目录行三处取到哪个算哪个"""
    if tree_name:
        return tree_name
    if item is not None:
        return item.distribution

    return release.distribution if release is not None else ""


def _row(
    platform: str,
    distribution: str,
    source: ComponentSource,
    installed: str,
    requires: str,
    release: ReleaseRow | None,
) -> ComponentRow:
    """拼一行组件，归属档由来路、本机版本与目录行比出来"""
    return ComponentRow(
        platform=platform,
        distribution=distribution,
        source=source,
        installed=installed,
        requires=requires,
        release=release,
        bucket=_bucket_of(source, installed, release),
    )


def _bucket_of(
    source: ComponentSource, installed: str, release: ReleaseRow | None
) -> ComponentBucket:
    """一行组件归到哪一档

    - 目录里没有这一只即只有本机有
    - 环境里没那只包即归网络可装，源码仓挂着也一样要先装
    - 源码仓挂着且包已装进环境即归本机已有，再装一次换不掉源码仓那份声明
    - 本机版本号读不懂即归本机已有，宁可不动也不按猜测装新版
    """
    if release is None:
        return ComponentBucket.LOCAL
    if not installed:
        return ComponentBucket.ONLINE
    if source == ComponentSource.TREE_INSTALLED:
        return ComponentBucket.LOCAL
    if is_upgrade(installed, release.version) is True:
        return ComponentBucket.UPGRADABLE

    return ComponentBucket.LOCAL


def _source_of(in_tree: bool, has_package: bool) -> ComponentSource:
    """代码与声明从哪来，挂载仓那份与已装包各记各的"""
    if in_tree:
        return (
            ComponentSource.TREE_INSTALLED if has_package else ComponentSource.TREE_ONLY
        )
    if has_package:
        return ComponentSource.INSTALLED

    return ComponentSource.NONE


def _releases_by_code(catalog: Catalog | None) -> dict[str, ReleaseRow]:
    """目录行按平台码归表，接口包那行记在空位下"""
    if catalog is None:
        return {}
    rows = {str(platform): release for platform, release in catalog.adapters.items()}
    if catalog.sdk is not None:
        rows[_SDK_CODE] = catalog.sdk

    return rows


def _installed_by_platform() -> dict[str, InstalledAdapter]:
    """已装适配器按平台码归表"""
    return {str(item.platform): item for item in installed_adapters()}


def _declared_requires() -> dict[str, str]:
    """本机在场适配器声明的接口包版本要求，按平台码归表"""
    return {
        str(dto.platform): dto.requires_sdk for dto in load_adapter_manifests().values()
    }
