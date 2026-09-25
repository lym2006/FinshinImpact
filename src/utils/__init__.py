# src/utils/__init__.py
"""通用工具门面

- 提供网络、日志、配置、生命周期出口
"""

from ._base_client import BaseClient
from ._check_version import check_updates
from ._config_manager import config_manager
from ._proxy_check import diagnose_plan, iter_diagnose
from ._root_dir import ROOT_DIR
from ._single_instance import acquire_instance_lock
from ._system_proxy import detect_system_proxy, scan_proxy_ports
from .init_files import (
    BLACKLIST_DIR,
    BLACKLIST_FILE,
    DOCS_DIR,
    LOGS_DIR,
    RECORDS_DIR,
    STAGED_DIR,
    TEMP_DIR,
)
from .lifecycle import register_lifecycle, unregister_lifecycle
from .logger import get_logger

__all__ = [
    # 全局路径
    "ROOT_DIR",
    "RECORDS_DIR",
    "TEMP_DIR",
    "STAGED_DIR",
    "DOCS_DIR",
    "LOGS_DIR",
    "BLACKLIST_DIR",
    "BLACKLIST_FILE",
    # 基础设施
    "BaseClient",
    "check_updates",
    "get_logger",
    "config_manager",
    "acquire_instance_lock",
    "diagnose_plan",
    "iter_diagnose",
    "detect_system_proxy",
    "scan_proxy_ports",
    # 生命周期
    "register_lifecycle",
    "unregister_lifecycle",
]
