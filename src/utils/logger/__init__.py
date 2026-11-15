"""日志门面

- 日志器与格式器出口
"""

import logging
import threading
from typing import cast

from finshin_sdk import LogLevel, bind_logger

from ..paths import BOT_LOG, DEBUG_LOG
from ._enhancer import BotLogger
from ._formatter import create_formatter
from ._handler import create_file_handler

_initialized = False  # 模块级状态
_setup_lock = threading.Lock()

# 派生格式器：文件日志自用，仪表盘那份对外
_FORMATTER = create_formatter()
GUI_FORMATTER = create_formatter(marked=True)


__all__ = [
    # 获取日志器
    "get_logger",
    # 增强型日志器类
    "BotLogger",
    # 仪表盘日志格式（带语义标记）
    "GUI_FORMATTER",
]

logging.setLoggerClass(BotLogger)

# 档位转标准库日志级别
_LEVELS: dict[LogLevel, int] = {
    LogLevel.DEBUG: logging.DEBUG,
    LogLevel.INFO: logging.INFO,
    LogLevel.ERROR: logging.ERROR,
}


def _public_sink(
    source: str, level: LogLevel, msg: str, exc: BaseException | None
) -> None:
    """接口包日志公开件的实现

    - 带异常即补一行调试档，调用链由异常本体交出
    """
    logger = get_logger(source)
    logger.log(_LEVELS[level], msg)
    if exc is not None:
        logger.debug(exc, exc_info=exc)


bind_logger(_public_sink)


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
        bot_logger.addHandler(create_file_handler(_FORMATTER, BOT_LOG))
        bot_logger.addHandler(create_file_handler(_FORMATTER, DEBUG_LOG, logging.DEBUG))

        # 事件库把处理函数的崩错只记在自己那只日志器上，根日志器静音就一起吞了
        logging.getLogger("aiogram").addHandler(
            create_file_handler(_FORMATTER, DEBUG_LOG, logging.ERROR)
        )
        _initialized = True  # 此后走无锁快速路径

    return logger
