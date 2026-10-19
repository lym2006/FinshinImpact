# src/utils/logger/__init__.py
"""日志门面

- 提供日志器与格式器出口
"""

import logging
import threading
from typing import cast

from ..init_files import BOT_LOG, DEBUG_LOG
from ._enhancer import BotLogger
from ._formatter import create_formatter
from ._handler import create_file_handler

_initialized = False  # 模块级状态
_setup_lock = threading.Lock()

# 全局派生格式器（对外提供）
FORMATTER = create_formatter()
GUI_FORMATTER = create_formatter(marked=True)
__all__ = [
    # 获取日志器
    "get_logger",
    # 增强型日志器类
    "BotLogger",
    # 日志格式
    "FORMATTER",
    # 仪表盘日志格式（带语义标记）
    "GUI_FORMATTER",
]

# 在模块加载时，接管全局 Logger 类
logging.setLoggerClass(BotLogger)


def get_logger(name: str = "") -> BotLogger:
    """获取 Bot 日志器"""
    global _initialized

    name = "Bot." + name if name else "Bot"
    logger = cast(BotLogger, logging.getLogger(name))

    # 快速路径：已初始化，直接返回（无锁开销）
    if _initialized:
        return logger

    # 慢速路径：需要初始化，加锁保护
    with _setup_lock:
        if _initialized:  # 双重检查，防止两个线程同时进入后重复初始化
            return logger

        # 根 Logger 静默
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.CRITICAL + 1)

        # Bot Logger
        bot_logger = logging.getLogger("Bot")
        bot_logger.setLevel(logging.DEBUG)
        bot_logger.propagate = False  # 绝对不向根 Logger 冒泡

        # 文件 Handler（简化版与详细版）
        bot_logger.addHandler(create_file_handler(FORMATTER, BOT_LOG))
        bot_logger.addHandler(create_file_handler(FORMATTER, DEBUG_LOG, logging.DEBUG))
        _initialized = True  # 标记初始化完成

    return logger
