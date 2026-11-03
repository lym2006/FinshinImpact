# src/utils/logger/_handler.py
"""文件日志处理器

- 轮转与编码统一的文件写入
- 改名被占用挡住即本轮不轮转，继续往原文件追加
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

_MAX_BYTES = 10 * 1024 * 1024  # 单文件上限（MB）
_BACKUP_COUNT = 2  # 旧文件保留份数


class _PatientFileHandler(RotatingFileHandler):
    """被占用时先不轮转的轮转写入"""

    def doRollover(self) -> None:  # noqa: N802
        """改名失败即重新以追加方式打开原文件

        - 上限判定照旧，占用一释放下一轮就正常轮转
        """
        try:
            super().doRollover()
        except OSError:
            if self.stream:
                self.stream.close()
            self.stream = self._open()


def create_file_handler(
    formatter: logging.Formatter,
    log_path: Path,
    level: int = logging.INFO,
) -> _PatientFileHandler:
    """创建文件输出 Handler"""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handler = _PatientFileHandler(
        log_path,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    handler.setFormatter(formatter)
    handler.setLevel(level)
    return handler
