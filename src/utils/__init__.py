# src/utils/__init__.py
"""通用工具门面

- 只导出多消费方的基础符号，低消费模块由调用方直连子模块
- 路径常量按消费方裁剪，内部中间路径不外露
"""

from ._config_manager import config_manager
from ._root_dir import ROOT_DIR
from .init_files import BLACKLIST_DIR, LOGS_DIR, RECORDS_DIR, TEMP_DIR
from .lifecycle import register_lifecycle, unregister_lifecycle
from .logger import get_logger

__all__ = [
    # 全局路径
    "ROOT_DIR",
    "RECORDS_DIR",
    "TEMP_DIR",
    "LOGS_DIR",
    "BLACKLIST_DIR",
    # 基础服务
    "config_manager",
    "get_logger",
    "register_lifecycle",
    "unregister_lifecycle",
]
