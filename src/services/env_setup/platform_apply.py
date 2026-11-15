"""平台组件的装卸动作

- 装一批按目录行取件，再一条命令装进运行环境
- 卸一只先数实例，再算只属于那只包的发行件名
- 镜像次序由取件与装机那两侧各自定
"""

from collections.abc import Sequence

from finshin_sdk.domain import platform_of_profile
from skin.messages import PlatformMessage

from ..adapter_catalog import ReleaseRow
from ..adapter_manifest import installed_adapters
from ..profile_store import list_profiles
from .deps_keep import keep_union
from .deps_manifest import top_package_name
from .subprocess_ops import ProgressCallback
from .toolchain import GITHUB_MIRRORS, WHEELS_DIR
from .wheel_fetch import download_release
from .wheel_install import WheelFile, install_releases


def instances_of(platform: str) -> int:
    """本机还有几个这一平台的实例

    - 认不出平台的目录不算任何平台的实例
    """
    return sum(
        1 for code, _remark in list_profiles() if platform_of_profile(code) == platform
    )


def uninstall_names(platform: str) -> tuple[str, ...]:
    """卸一只平台适配器要动的发行件名

    - 适配器包自身，加只有这一只声明过的库
    - 核心依赖、接口包、别只适配器与启用插件点过的库一律留下
    - 传递依赖不在这里算，同步环境那一步收口
    """
    target = next(
        (item for item in installed_adapters() if str(item.platform) == platform), None
    )
    if target is None:
        return ()

    kept = {top_package_name(pin) for pin in keep_union(exclude=target.platform)}
    alone = [
        name for name in map(top_package_name, target.requires) if name not in kept
    ]

    return tuple([target.distribution, *alone])


async def apply_updates(
    releases: Sequence[ReleaseRow], on_line: ProgressCallback | None = None
) -> list[str]:
    """按目录行取件并装进运行环境，交出点名到发行件的失败行"""
    files: list[WheelFile] = []
    notes: list[str] = []
    for release in releases:
        if on_line is not None:
            on_line(PlatformMessage.LINE_FETCHING.format(name=release.distribution))
        outcome = await download_release(release, WHEELS_DIR, GITHUB_MIRRORS)
        if outcome.path is None:
            notes.append(outcome.note)
            continue
        files.append(WheelFile(outcome.distribution, outcome.path))

    if files:
        notes.extend(install_releases(files, on_line))

    return notes
