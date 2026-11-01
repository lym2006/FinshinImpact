# src/utils/logger/_enhancer.py
"""双轨日志器

- 面向用户与开发者双轨输出
"""

import logging
import sys
from typing import Any


class BotLogger(logging.Logger):
    """Bot 专属的增强型日志器"""

    def __init__(self, name: str, level: int = logging.NOTSET) -> None:
        super().__init__(name, level)

    def debug(self, msg: object, *args: object, **kwargs: Any) -> None:
        """调试记录默认带堆栈

        - 异常在场即附上异常本体与调用链
        - 无异常在场时只落单行
        """
        kwargs.setdefault("exc_info", sys.exc_info()[0] is not None)
        super().debug(msg, *args, **kwargs)

    def send_error(self, msg: str, e: object) -> None:
        """写入报错日志

        - 分层 GUI 和文件
        """
        self.error(msg)
        self.debug(e)
