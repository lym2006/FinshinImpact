# src/utils/logger/__init__.py
# src/utils/logger/__init__.py
"""
Bot 日志器工具入口

导出：
- 初始化并配置 Bot 专属日志器的方法
"""

from .setup import setup_logger

__all__ = [
    # 配置 Bot 专属日志器
    "setup_logger"
]
