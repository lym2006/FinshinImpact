"""平台组件面板的在线目录取数线程

- 取到交出目录，取不到交出一行给人看的原因
- 失败原文进运行日志，屏上那句只到异常族给的为止
"""

import asyncio
import traceback

from PySide6.QtCore import QThread, Signal

from exceptions import NetworkError, describe_error
from services.adapter_catalog import load_catalog
from services.env_setup.subprocess_ops import log_ops
from skin.messages import PlatformMessage


class CatalogTask(QThread):
    """在线目录后台取数线程"""

    reported = Signal(object, str)

    def run(self) -> None:
        """取一次在线目录，两种坏法各落一行原因"""
        try:
            self.reported.emit(asyncio.run(load_catalog()), "")
        except NetworkError as e:
            log_ops(traceback.format_exception(e))
            self.reported.emit(
                None, PlatformMessage.FETCH_FAILED.format(reason=describe_error(e))
            )
        except Exception as e:
            log_ops([f"[task:catalog] {type(e).__name__}: {e}"])
            self.reported.emit(
                None, PlatformMessage.FETCH_FAILED.format(reason=type(e).__name__)
            )
