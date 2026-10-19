# src/utils/logger/_handler.py
"""文件日志处理器（内部实现）

- 定义轮转与编码统一的文件写入
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

_MAX_BYTES = 10 * 1024 * 1024  # 单文件上限（MB）
_BACKUP_COUNT = 2  # 旧文件保留份数


def create_file_handler(
    formatter: logging.Formatter,
    log_path: Path,
    level: int = logging.INFO,
) -> RotatingFileHandler:
    """创建文件输出 Handler"""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        log_path,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    handler.setFormatter(formatter)
    handler.setLevel(level)
    return handler
