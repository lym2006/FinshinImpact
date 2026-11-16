"""平台组件的装与挡

- 一键更新的那批只收在线比本机新的行
- 适配器要接口包已在本机，且落在它声明的版本要求之内
- 接口包要求那一行的说法按本机接口包版本定
- 可装的旧版逐版报来路，盘上的件逐份报核没核到指纹
"""

from collections.abc import Sequence
from dataclasses import dataclass

from skin.messages import PlatformMessage
from system.distributions import SDK_DISTRIBUTION, installed_version
from system.versions import over_ceiling, requires_met

from ..adapter_catalog import ReleaseRow
from .platform_rows import ComponentBucket, ComponentRow, ComponentSource
from .toolchain import WHEELS_DIR
from .wheel_fetch import disk_files, file_name_of, is_cached


@dataclass(frozen=True, slots=True)
class VersionLine:
    """版本清单里一版可装件的读数

    - installed 是本机环境里就是这一版，cached 是盘上那份件对得上目录指纹
    """

    release: ReleaseRow
    installed: bool
    cached: bool


@dataclass(frozen=True, slots=True)
class WheelLine:
    """盘上一份 wheel 件的读数

    - listed 是这份件对得上目录里的某一版，对不上即没有权威指纹可核
    """

    file_name: str
    listed: bool


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


def older_versions(row: ComponentRow) -> tuple[VersionLine, ...]:
    """版本清单里除最新一版外的每一版，装旧版即回退

    - 没有目录行即没有清单可列
    - 挡不挡装由适配器那一行的接口包要求定，逐版不另判
    """
    if row.release is None:
        return ()

    return tuple(
        VersionLine(
            release=item,
            installed=bool(row.installed) and item.version == row.installed,
            cached=is_cached(item, WHEELS_DIR),
        )
        for item in row.release.versions[1:]
    )


def local_wheels(row: ComponentRow) -> tuple[WheelLine, ...]:
    """盘上属于这只发行件的每一份件，对不上目录任何一版的即没权威指纹可核

    - 没有目录行时盘上的件一律算对不上
    """
    listed = (
        {file_name_of(item.url) for item in row.release.versions}
        if row.release is not None
        else set()
    )

    return tuple(
        WheelLine(file_name=name, listed=name in listed)
        for name in disk_files(row.distribution, WHEELS_DIR)
    )


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
