# src/utils/logger/enhance.py
"""
Bot 日志器增强模块

提供：
- 为指定 Logger 注入自动 exc_info 捕获逻辑
"""

import logging
import sys


def enhance_logger(logger: logging.Logger) -> None:
    """
    为指定的 Logger 增强 error 方法

    当调用 error 且未手动传入 exc_info 时，自动捕获当前异常堆栈
    """
    original_error = logger.error

    def _enhanced_error(*args, **kwargs) -> None:
        """传入 exc_info"""
        if "exc_info" not in kwargs and sys.exc_info()[0] is not None:
            kwargs["exc_info"] = True
        return original_error(*args, **kwargs)

    logger.error = _enhanced_error
