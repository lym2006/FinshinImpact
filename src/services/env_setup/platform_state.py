"""平台组件的装与挡

- 一键更新的那批只收在线比本机新的行
- 适配器要接口包已在本机，且落在它声明的版本要求之内
- 接口包要求那一行的说法按本机接口包版本定
"""

from collections.abc import Sequence

from skin.messages import PlatformMessage
from system.distributions import SDK_DISTRIBUTION, installed_version
from system.versions import over_ceiling, requires_met

from ..adapter_catalog import ReleaseRow
from .platform_rows import ComponentBucket, ComponentRow, ComponentSource


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
