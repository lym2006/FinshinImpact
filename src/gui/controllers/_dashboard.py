# src/gui/controllers/_dashboard.py
"""仪表盘控制器

- 实现日志清空与退出按钮逻辑
"""

from ._base import BaseController


class DashboardController(BaseController):
    """仪表盘控制器"""

    # 契约声明
    LOGGER_NAME = "GUI.Dashboard"
    BTN_KEY = "clear"

    def _execute(self) -> None:
        """清空仪表盘内容"""
        self.gui.clear_dashboard()
        self.logger.info("仪表盘已清理")
