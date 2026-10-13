# src/utils/__init__.py
"""通用工具门面

- 只导出多消费方的基础符号
- 路径常量由消费方直连 utils.paths，不经门面转发
"""

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
