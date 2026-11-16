"""环境维护入口

- 本机管理菜单并列三项：平台组件、同步重建与清理缓存
- 保留清单取全实例启用并集，操作对象为共享 runtime 依赖层
- 同步重建会删保留清单外的包，只由这个菜单发起
"""

from PySide6.QtCore import QPoint
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QMenu,
    QPushButton,
    QWidget,
)

from services.env_setup.deps_install import sync_env
from services.env_setup.deps_keep import keep_conflicts, keep_union
from services.env_setup.subprocess_ops import ProgressCallback, clean_cache
from skin.messages import PluginMessage

from ._platform import open_platform_dialog
from ._popup import confirm_popup
from ._progress import run_with_progress


def _sync_flow(parent: QWidget | None) -> list[str]:
    """二次确认后按保留清单重建环境"""
    if not confirm_popup(
        PluginMessage.SETTLE_TITLE, PluginMessage.SYNC_WARNING, parent
    ):
        return []
    return run_with_progress(
        PluginMessage.PROGRESS_SYNC,
        lambda on_line: sync_env(keep_union(), on_line, keep_conflicts()),
    )


def _cache_task(on_line: ProgressCallback | None = None) -> list[str]:
    """清空下载缓存，本操作无失败项概念恒回空表"""
    clean_cache(on_line)
    return []


def _cache_flow(parent: QWidget | None) -> list[str]:
    """二次确认后清空 uv 下载缓存"""
    if not confirm_popup(
        PluginMessage.SETTLE_TITLE, PluginMessage.CACHE_WARNING, parent
    ):
        return []
    return run_with_progress(PluginMessage.PROGRESS_CACHE, _cache_task)


def open_maintain_menu(anchor: QPushButton, parent: QWidget) -> None:
    """在锚点按钮上方弹出本机管理菜单

    - parent 挂宿主窗口，选窗开着也能定位置顶
    """
    menu = QMenu(parent)

    component_action = QAction(PluginMessage.MENU_PLATFORM, menu)
    component_action.triggered.connect(lambda: open_platform_dialog(parent))
    sync_action = QAction(PluginMessage.MENU_SYNC, menu)
    sync_action.triggered.connect(lambda: _sync_flow(parent))
    cache_action = QAction(PluginMessage.MENU_CACHE, menu)
    cache_action.triggered.connect(lambda: _cache_flow(parent))

    menu.addAction(component_action)
    menu.addAction(sync_action)
    menu.addAction(cache_action)

    # 向上弹出贴着按钮，避免菜单越出屏幕下缘
    top_left = anchor.mapToGlobal(anchor.rect().topLeft())
    size = menu.sizeHint()
    menu.exec(QPoint(top_left.x(), top_left.y() - size.height()))
    menu.deleteLater()
