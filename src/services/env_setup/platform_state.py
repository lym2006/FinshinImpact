"""平台组件读数

- 一份读数并上在线目录行，接口包在最前
- 归属档按本机来路、本机版本与在线版本比出来，版本串读不懂算本机已有
- 来源与发行件名按同一条规则排，接口包与适配器不分两样
"""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from finshin_sdk.domain import Platform
from skin.messages import PlatformMessage
from system.distributions import SDK_DISTRIBUTION, installed_version
from system.profile_env import DECLARATION_FILE_NAME, ROOT_DIR
from system.tool_settings import project_value
from system.versions import floor_met, is_upgrade

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

    - TREE 挂载的源码仓在场，声明按它读
    - INSTALLED 声明与代码都取环境里那只包
    - NONE 本机没有
    """

    TREE = "tree"
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
    - installed 与 floor 各留各的空串，本机没在场即是空
    - release 在场才有得装，目录行自带直链与指纹
    """

    platform: str
    distribution: str
    source: ComponentSource
    installed: str
    floor: str
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


def update_targets(rows: Sequence[ComponentRow]) -> list[ReleaseRow]:
    """一键更新的那批目录行，只收在线比本机新的

    - 本机没装过的不进这一批，装哪个平台由逐行的按钮定
    """
    return [
        row.release
        for row in rows
        if row.release is not None and row.bucket == ComponentBucket.UPGRADABLE
    ]


def install_blocked(rows: Sequence[ComponentRow], row: ComponentRow) -> str:
    """这只组件现在不该给安装，交出那句下一步，能装交出空串

    - 适配器要接口包已在本机，还须达到它声明的下限
    - 接口包自己不受这条限制
    - 版本串读不懂算没到位
    """
    if not row.platform:
        return ""
    sdk = next((item for item in rows if not item.platform), None)
    if sdk is None or not sdk.installed:
        return PlatformMessage.NEED_SDK_INSTALL
    if not row.floor:
        return ""

    return (
        "" if floor_met(sdk.installed, row.floor) else PlatformMessage.NEED_SDK_UPDATE
    )


def deps_text(row: ComponentRow) -> str:
    """接口包要求那一行的正文，按本机接口包版本定说法

    - 接口包那行没有要求可报，本机没在场的行也一样
    """
    if not row.platform or row.source == ComponentSource.NONE:
        return ""
    if not row.floor:
        return PlatformMessage.FLOOR_NONE

    actual = installed_version(SDK_DISTRIBUTION)
    if not actual:
        return PlatformMessage.FLOOR_NO_SDK.format(floor=row.floor)

    met = floor_met(actual, row.floor)
    if met is None:
        return PlatformMessage.FLOOR_UNREADABLE.format(floor=row.floor)

    return (PlatformMessage.FLOOR_MET if met else PlatformMessage.FLOOR_GAP).format(
        floor=row.floor, actual=actual
    )


def _rows(catalog: Catalog | None) -> tuple[ComponentRow, ...]:
    """按本机在场件与目录行排出组件行，接口包在最前"""
    installed = _installed_by_platform()
    floors = {str(platform): floor for platform, floor in _declared_floors().items()}
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
        set(installed) | set(floors) | set(tree) | (set(releases) - {_SDK_CODE})
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
                floors.get(code, ""),
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
    floor: str,
    release: ReleaseRow | None,
) -> ComponentRow:
    """拼一行组件，归属档由来路、本机版本与目录行比出来"""
    return ComponentRow(
        platform=platform,
        distribution=distribution,
        source=source,
        installed=installed,
        floor=floor,
        release=release,
        bucket=_bucket_of(source, installed, release),
    )


def _bucket_of(
    source: ComponentSource, installed: str, release: ReleaseRow | None
) -> ComponentBucket:
    """一行组件归到哪一档

    - 没有目录行即只在本机
    - 本机没那只包即只在网络，源码仓挂着也一样要装
    - 源码仓挂着且已装包即算本机已有，装了只换代码不换声明
    - 版本串读不懂算本机已有，不拿猜的新版去装
    """
    if release is None:
        return ComponentBucket.LOCAL
    if not installed:
        return ComponentBucket.ONLINE
    if source == ComponentSource.TREE:
        return ComponentBucket.LOCAL
    if is_upgrade(installed, release.version) is True:
        return ComponentBucket.UPGRADABLE

    return ComponentBucket.LOCAL


def _source_of(in_tree: bool, has_package: bool) -> ComponentSource:
    """代码与声明从哪来，挂载仓那份优先于已装包"""
    if in_tree:
        return ComponentSource.TREE
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


def _declared_floors() -> dict[Platform, str]:
    """本机在场适配器声明的接口包下限"""
    return {
        platform: dto.requires_sdk for platform, dto in load_adapter_manifests().items()
    }
