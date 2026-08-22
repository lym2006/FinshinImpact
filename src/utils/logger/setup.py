# src/utils/logger/setup.py
"""
全局日志系统配置

提供：
- 控制台与文件双路日志输出
- 专属 Bot 日志器自动异常堆栈捕获
- 第三方库噪音屏蔽
"""

import logging

from .enhance import enhance_logger
from .filters import suppress_third_party_logs
from .handlers import create_console_handler, create_file_handler


def setup_logger() -> logging.Logger:
    """初始化全局日志系统"""
    logger = logging.getLogger("Bot")

    # 防止重复添加 Handler（热重载时）
    if logger.handlers:
        return logger

    # 设置 Bot 自身的日志级别
    logger.setLevel(logging.INFO)

    # 日志格式器
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(name)-25s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 控制台输出
    logger.addHandler(create_console_handler(formatter))

    # 文件输出
    logger.addHandler(create_file_handler(formatter=formatter))

    # 第三方库噪音屏蔽
    suppress_third_party_logs()

    # 自动堆栈增强
    enhance_logger(logger)

    return logger
