# src/gui/controllers/_system.py
"""日志控制器

- 提供打开日志目录入口
"""

from skin.messages import MiscMessage
from system.shell import activate_explorer, open_path
from utils.paths import LOGS_DIR

from ._base import BaseController


class LogsController(BaseController):
    """日志控制器"""

    # 契约声明
    LOGGER_NAME = "GUI.Logs"
    BTN_KEY = "log"

    def _execute(self) -> None:
        """打开日志文件所在目录"""
        self.logger.info("正在打开日志文件目录...")
        try:
            # 成功与置前都不落日志：窗口出现即结果，只留发起与失败
            if not activate_explorer(LOGS_DIR.name):
                open_path(LOGS_DIR)

        except OSError as e:
            # 路径空格、权限不足、explorer 崩溃等系统级错误统一兜底
            self.logger.send_error(MiscMessage.OPEN_LOGS_FAIL, e)

        except Exception as e:
            # 防止任何未知异常导致 GUI 闪退
            self.logger.send_error(MiscMessage.UNKNOWN_ERROR, e)
