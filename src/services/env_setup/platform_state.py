"""平台组件的装与挡

- 一键更新的那批只收在线比本机新的行，接口包那行先算在场适配器的要求
- 适配器要接口包已在本机，且落在它声明的版本要求之内
- 接口包要求那一行的说法按本机接口包版本定
- 可装的旧版逐版报来路，盘上的件逐份报核没核到指纹
"""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from skin.messages import PlatformMessage
from system.distributions import SDK_DISTRIBUTION, installed_version
from system.versions import is_upgrade, over_ceiling, requires_met

from ..adapter_catalog import ReleaseRow
from .platform_rows import ComponentBucket, ComponentRow, ComponentSource
from .toolchain import WHEELS_DIR
from .wheel_fetch import disk_files, file_name_of, is_cached, local_release


class ComponentOrigin(StrEnum):
    """一行摆的内容从哪儿取到

    - WHEEL 盘上那份件指纹对得上目录，装它不联网
    - CATALOG 只有在线目录的直链，装它要走网络
    - TREE 没有目录行，只有挂载的源码仓在场
    - NONE 本机既没有目录行也没有源码仓
    """

    WHEEL = "wheel"
    CATALOG = "catalog"
    TREE = "tree"
    NONE = "none"


@dataclass(frozen=True, slots=True)
class VersionLine:
    """版本清单里一版可装件的读数

    - installed 是本机环境里就是这一版，cached 是盘上那份件对得上目录指纹
    - blocked 交出那句装不了的理由，能装交出空串
    """

    release: ReleaseRow
    installed: bool
    cached: bool
    blocked: str


class WheelOrigin(StrEnum):
    """盘上一份件的来路

    - CATALOG 目录里有这一版，装它按目录给的指纹核
    - RECORDED 目录里没有而本机下载时记过指纹，装它直接用盘上那份
    - UNKNOWN 两样都没有，没有权威值可核
    """

    CATALOG = "catalog"
    RECORDED = "recorded"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class WheelLine:
    """盘上一份 wheel 件的读数

    - release 是能装时那一版的目标，装不了即空
    - blocked 交出那句装不了的理由，能装交出空串
    """

    file_name: str
    origin: WheelOrigin
    release: ReleaseRow | None
    blocked: str


def update_targets(rows: Sequence[ComponentRow]) -> list[ReleaseRow]:
    """一键更新的那批目录行，只收在线比本机新的

    - 本机没装过的不进这一批，装哪个平台由逐行的按钮定
    - 接口包推不出在场适配器要求的那批不进这一批
    """
    targets: list[ReleaseRow] = []
    for row in rows:
        if row.bucket != ComponentBucket.UPGRADABLE:
            continue
        target = update_target(rows, row)
        if target is not None:
            targets.append(target)

    return targets


def update_target(rows: Sequence[ComponentRow], row: ComponentRow) -> ReleaseRow | None:
    """这一行该装的那一版，没得更动交出 None

    - 适配器那行取目录最新一版
    - 接口包那行取满足在场每只适配器要求里最新的一版，本机没装过时不比本机
    """
    if row.release is None:
        return None
    if row.platform:
        return row.release

    for item in row.release.versions:
        newer = not row.installed or is_upgrade(row.installed, item.version) is True
        if newer and _sdk_in_range(rows, item.version):
            return item

    return None


def release_blocked(
    rows: Sequence[ComponentRow], row: ComponentRow, release: ReleaseRow
) -> str:
    """装这一版该不该挡，交出那句理由，能装交出空串

    - 适配器那行按本机接口包落在不在它声明的要求之内判
    - 接口包那行按这一版满不满足在场每只适配器声明的要求判
    """
    if row.platform:
        return _install_blocked(rows, row)
    if _sdk_in_range(rows, release.version):
        return ""

    return PlatformMessage.SDK_RANGE_GAP


def _declared_ranges(rows: Sequence[ComponentRow]) -> tuple[str, ...]:
    """在场适配器各自声明的接口包要求，没装进环境的不算在场"""
    return tuple(
        row.requires for row in rows if row.platform and row.installed and row.requires
    )


def _sdk_in_range(rows: Sequence[ComponentRow], version: str) -> bool:
    """这一版接口包是否落在在场每只适配器声明的要求之内

    - 要求串或版本串读不懂算不满足
    """
    return all(
        requires_met(version, requires) is True for requires in _declared_ranges(rows)
    )


def _install_blocked(rows: Sequence[ComponentRow], row: ComponentRow) -> str:
    """这只组件现在不该给安装，交出那句下一步，能装交出空串

    - 适配器要接口包已在本机，且落在它声明的版本要求之内
    - 接口包自己不受这条限制
    - 版本串读不懂算没到位
    """
    if not row.platform:
        return ""
    sdk = next((item for item in rows if not item.platform), None)
    if sdk is None or not sdk.installed:
        return PlatformMessage.NEED_SDK_INSTALL
    if requires_met(sdk.installed, row.requires):
        return ""
    if over_ceiling(sdk.installed, row.requires):
        return PlatformMessage.SDK_TOO_NEW

    return PlatformMessage.NEED_SDK_UPDATE


def source_origin(rows: Sequence[ComponentRow], row: ComponentRow) -> ComponentOrigin:
    """一行摆的内容从哪儿取到，按该装的那一版的件在不在盘上定

    - 没有该装的那一版时，源码仓挂着只说明声明读得到
    """
    target = update_target(rows, row)
    if target is None:
        in_tree = row.source in (
            ComponentSource.TREE_INSTALLED,
            ComponentSource.TREE_ONLY,
        )
        return ComponentOrigin.TREE if in_tree else ComponentOrigin.NONE
    if is_cached(target, WHEELS_DIR):
        return ComponentOrigin.WHEEL

    return ComponentOrigin.CATALOG


def older_versions(
    rows: Sequence[ComponentRow], row: ComponentRow
) -> tuple[VersionLine, ...]:
    """版本清单里除最新一版外的每一版，装旧版即回退

    - 没有目录行即没有清单可列
    - 逐版各判一次挡不挡，接口包那行的旧版可能正落在在场适配器要求之外
    """
    if row.release is None:
        return ()

    return tuple(
        VersionLine(
            release=item,
            installed=bool(row.installed) and item.version == row.installed,
            cached=is_cached(item, WHEELS_DIR),
            blocked=release_blocked(rows, row, item),
        )
        for item in row.release.versions[1:]
    )


def local_wheels(
    rows: Sequence[ComponentRow], row: ComponentRow
) -> tuple[WheelLine, ...]:
    """盘上属于这只发行件的每一份件，按目录与本机记录两样定来路

    - 目录取不到时，本机记过指纹的那几份仍算可装
    - 两样都没有即没有权威值可核，那一份不给装
    """
    listed = (
        {file_name_of(item.url): item for item in row.release.versions}
        if row.release is not None
        else {}
    )
    lines: list[WheelLine] = []
    for name in disk_files(row.distribution, WHEELS_DIR):
        release = listed.get(name) or local_release(row.distribution, name, WHEELS_DIR)
        lines.append(
            WheelLine(
                file_name=name,
                origin=_origin_of(name, listed, release),
                release=release,
                blocked=(
                    release_blocked(rows, row, release) if release is not None else ""
                ),
            )
        )

    return tuple(lines)


def _origin_of(
    name: str, listed: dict[str, ReleaseRow], release: ReleaseRow | None
) -> WheelOrigin:
    """那份件的来路，目录里有即按目录那一版，只有本机记过即按本机"""
    if name in listed:
        return WheelOrigin.CATALOG
    if release is not None:
        return WheelOrigin.RECORDED

    return WheelOrigin.UNKNOWN


def deps_text(row: ComponentRow) -> str:
    """接口包要求那一行的正文，按本机接口包版本定说法

    - 接口包那行没有要求可报，本机没在场的行也一样
    """
    if not row.platform or row.source == ComponentSource.NONE:
        return ""
    if not row.requires:
        return PlatformMessage.REQUIRES_NONE

    actual = installed_version(SDK_DISTRIBUTION)
    if not actual:
        return PlatformMessage.REQUIRES_NO_SDK.format(requires=row.requires)

    met = requires_met(actual, row.requires)
    if met is None:
        return PlatformMessage.REQUIRES_UNREADABLE.format(requires=row.requires)

    return (
        PlatformMessage.REQUIRES_MET if met else PlatformMessage.REQUIRES_GAP
    ).format(requires=row.requires, actual=actual)
