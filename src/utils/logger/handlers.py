# src/utils/logger/handlers.py
"""
Bot 日志 Handler 创建模块

提供：
- 控制台输出 Handler（stdout）
- 文件输出 Handler（RotatingFileHandler，10MB 自动切割）
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def create_console_handler(formatter: logging.Formatter) -> logging.StreamHandler:
    """创建控制台输出 Handler"""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    return handler


def create_file_handler(
    log_path: Path = Path("logs/bot.log"),
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 2,
    formatter: logging.Formatter | None = None,
) -> RotatingFileHandler:
    """
    创建文件输出 Handler

    :param log_path: 日志文件路径
    :param max_bytes: 单个日志文件最大字节数，默认 10MB
    :param backup_count: 保留的旧文件数量，默认 2 个（2 旧 1 新）
    :param formatter: 日志格式器，未传则使用默认格式
    """
    log_path.parent.mkdir(parents=True, exist_ok=True)

    if formatter is None:
        from logging import Formatter

        formatter = Formatter(
            fmt="%(asctime)s | %(name)-25s | %(levelname)-8s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    handler = RotatingFileHandler(
        log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setFormatter(formatter)
    return handler
