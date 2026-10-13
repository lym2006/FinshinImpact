# src/bootstrap/_plugin/_maintain.py
"""环境维护入口

- 全局同步依赖经包门面供选窗调用
- 保留清单取全实例启用并集，操作对象为共享 runtime 依赖层
"""

from PySide6.QtWidgets import QMessageBox, QWidget

from app_icon import ensure_app
from messages import PluginMessage

from ._installer import sync_env
from ._manifest import core_dependencies, enabled_deps_union
from ._progress import run_with_progress


def _keep_union() -> list[str]:
    """全局保留清单

    - 核心依赖与全实例启用插件依赖并集
    - 本实例刚保存的启用集已在盘上，并集即最新状态
    """
    return [*core_dependencies(), *enabled_deps_union()]


def sync_environment(parent: QWidget | None = None) -> list[str]:
    """二次确认后按保留清单重建环境

    - parent 传入即挂宿主窗口，选窗开着也能定位置顶
    """
    ensure_app()
    confirmed = QMessageBox.question(
        parent,
        PluginMessage.SETTLE_TITLE,
        PluginMessage.SYNC_WARNING,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    if confirmed != QMessageBox.StandardButton.Yes:
        return []
    return run_with_progress(
        PluginMessage.PROGRESS_SYNC,
        lambda on_line: sync_env(_keep_union(), on_line),
    )
