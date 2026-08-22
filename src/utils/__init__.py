# src/utils/__init__.py
"""
全局通用工具

提供：
- 基础网络客户端与安全会话
- 全局配置与日志初始化
- 核心中间件与路由注册
"""

from .base_client import BaseClient
from .config_loader import CONFIG, ConfigError
from .init_files import init_project_files
from .logger import setup_logger
from .middlewares import LoggingMiddleware
from .plugins_register import register_routers
from .root_dir import ROOT_DIR
from .ssl import SafeSession

__all__ = [
    # 网络与基础设施
    "BaseClient",
    "SafeSession",
    # 全局配置与路径
    "CONFIG",
    "ConfigError",
    "ROOT_DIR",
    # 中间件与路由
    "LoggingMiddleware",
    "register_routers",
    # 初始化与日志
    "init_project_files",
    "setup_logger",
]
