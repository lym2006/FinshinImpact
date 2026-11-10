# src/utils/__init__.py
"""通用工具门面

- 只导出多消费方的基础符号
"""

# 路径常量不走这层转发，各消费方直连 paths 取
from ._config_manager import config_manager
from .lifecycle import register_lifecycle, unregister_lifecycle
from .logger import get_logger

__all__ = [
    # 基础服务
    "config_manager",
    "get_logger",
    # 生命周期
    "register_lifecycle",
    "unregister_lifecycle",
]
