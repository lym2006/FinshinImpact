# src/bootstrap/_plugin/_maintain.py
"""环境维护入口

- 依赖管理弹下拉菜单，同步重建与清理缓存两条操作并列
- 保留清单取全实例启用并集，操作对象为共享 runtime 依赖层
"""

from PySide6.QtCore import QPoint
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QMenu,
    QMessageBox,
    QPushButton,
    QWidget,
)

from skin.messages import PluginMessage
from system.app_icon import ensure_app

from ._installer import sync_env
from ._manifest import core_dependencies, enabled_deps_union
from ._progress import run_with_progress
from ._support import ProgressFn, clean_cache


def _keep_union() -> list[str]:
    """全局保留清单

    - 核心依赖与全实例启用插件依赖并集
    - 本实例刚保存的启用集已在盘上，并集即最新状态
    """
    return [*core_dependencies(), *enabled_deps_union()]


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
        lambda on_line: sync_env(_keep_union(), on_line),
    )


def _cache_task(on_line: ProgressFn | None = None) -> list[str]:
    """清空下载缓存，本操作无失败项概念恒回空表"""
    clean_cache(on_line)
    return []


def _cache_flow(parent: QWidget | None) -> list[str]:
    """二次确认后清空 uv 下载缓存"""
    if not _confirm(parent, PluginMessage.CACHE_WARNING):
        return []
    return run_with_progress(PluginMessage.PROGRESS_CACHE, _cache_task)


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
