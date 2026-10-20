# src/ui/_guide/_maintain.py
"""环境维护入口

- 依赖管理弹下拉菜单，同步重建与清理缓存两条操作并列
- 保留清单取全实例启用并集，操作对象为共享 runtime 依赖层
- 启动期对账不符调的也是这条同步流程
"""

from PySide6.QtCore import QPoint
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QMenu,
    QMessageBox,
    QPushButton,
    QWidget,
)

from services.env_setup.deps_install import sync_env
from services.env_setup.deps_manifest import keep_union
from services.env_setup.subprocess_ops import ProgressCallback, clean_cache
from skin.messages import PluginMessage

from .._lifecycle import ensure_app
from ._progress import run_with_progress


def _confirm(parent: QWidget | None, warning: str) -> bool:
    """大警告二次确认，默认停在否"""
    ensure_app()
    confirmed = QMessageBox.question(
        parent,
        PluginMessage.SETTLE_TITLE,
        warning,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    return confirmed == QMessageBox.StandardButton.Yes


def _sync_flow(parent: QWidget | None) -> list[str]:
    """二次确认后按保留清单重建环境"""
    if not _confirm(parent, PluginMessage.SYNC_WARNING):
        return []
    return run_with_progress(
        PluginMessage.PROGRESS_SYNC,
        lambda on_line: sync_env(keep_union(), on_line),
    )


def _cache_task(on_line: ProgressCallback | None = None) -> list[str]:
    """清空下载缓存，本操作无失败项概念恒回空表"""
    clean_cache(on_line)
    return []


def _cache_flow(parent: QWidget | None) -> list[str]:
    """二次确认后清空 uv 下载缓存"""
    if not _confirm(parent, PluginMessage.CACHE_WARNING):
        return []
    return run_with_progress(PluginMessage.PROGRESS_CACHE, _cache_task)


def sync_deps() -> None:
    """启动期依赖同步，此刻无宿主窗口即独立弹

    - 用户选否或同步失败都不落对账戳，下次启动清单仍不符再问
    """
    _sync_flow(None)


def open_maintain_menu(anchor: QPushButton, parent: QWidget) -> None:
    """在锚点按钮上方弹出依赖管理菜单

    - parent 挂宿主窗口，选窗开着也能定位置顶
    - 清缓存项带 danger 属性，由 QSS 标红
    """
    menu = QMenu(parent)

    sync_action = QAction(PluginMessage.MENU_SYNC, menu)
    sync_action.triggered.connect(lambda: _sync_flow(parent))
    cache_action = QAction(PluginMessage.MENU_CACHE, menu)
    cache_action.setProperty("danger", True)
    cache_action.triggered.connect(lambda: _cache_flow(parent))

    menu.addAction(sync_action)
    menu.addAction(cache_action)

    # 向上弹出贴着按钮，避免菜单越出屏幕下缘
    top_left = anchor.mapToGlobal(anchor.rect().topLeft())
    size = menu.sizeHint()
    menu.exec(QPoint(top_left.x(), top_left.y() - size.height()))
    menu.deleteLater()
