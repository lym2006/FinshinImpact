"""平台组件面板的装卸流程

- 装一批走进度窗，卸一只先查实例再二次确认
- 结果按发行件逐条上屏，做完交回面板重灌读数
"""

import asyncio
from collections.abc import Callable, Sequence

from PySide6.QtWidgets import QWidget

from services.adapter_catalog import ReleaseRow
from services.env_setup.deps_install import remove_distributions
from services.env_setup.platform_apply import (
    apply_updates,
    instances_of,
    uninstall_names,
)
from skin.messages import PlatformMessage
from skin.theme import PLATFORM_DIALOG

from ._popup import confirm_popup, show_popup
from ._progress import run_with_progress


def install_flow(on_done: Callable[[], None], releases: Sequence[ReleaseRow]) -> None:
    """进度窗里装一批发行件，装完交回面板重灌

    - 失败行逐条上屏，一条没报出来即点名未报原因
    """
    wanted = list(releases)
    if not wanted:
        return

    items = "、".join(f"{release.distribution} {release.version}" for release in wanted)
    failed = run_with_progress(
        PlatformMessage.WAIT_INSTALL.format(items=items),
        lambda on_line: asyncio.run(apply_updates(wanted, on_line)),
    )
    if failed:
        _report_done(
            on_done,
            PlatformMessage.INSTALL_PART_FAIL.format(
                items=items,
                notes="\n".join(str(note) for note in failed)
                or PlatformMessage.INSTALL_BLANK,
            ),
        )
        return

    show_popup(
        PLATFORM_DIALOG.title,
        PlatformMessage.INSTALL_DONE.format(items=items),
        icon_warning=False,
    )
    on_done()


def uninstall_flow(parent: QWidget, on_done: Callable[[], None], platform: str) -> None:
    """先查实例，再二次确认，最后在进度窗里卸包

    - 还有实例即只弹那一句拦路话
    """
    count = instances_of(platform)
    if count:
        show_popup(
            PLATFORM_DIALOG.title,
            PlatformMessage.UNINSTALL_BLOCKED.format(platform=platform, count=count),
        )
        return

    names = list(uninstall_names(platform))
    if not names:
        return
    if not confirm_popup(
        PLATFORM_DIALOG.title,
        PlatformMessage.UNINSTALL_ASK.format(platform=platform),
        parent,
    ):
        return

    failed = run_with_progress(
        PlatformMessage.WAIT_REMOVE.format(name="、".join(names)),
        lambda on_line: remove_distributions(names, on_line),
    )
    if failed:
        _report_done(on_done, "\n".join(str(note) for note in failed))
        return

    show_popup(
        PLATFORM_DIALOG.title,
        PlatformMessage.UNINSTALL_DONE.format(platform=platform),
        icon_warning=False,
    )
    on_done()


def _report_done(on_done: Callable[[], None], body: str) -> None:
    """摆出坏的那一侧，再交回面板重灌读数"""
    show_popup(PLATFORM_DIALOG.title, body)
    on_done()
