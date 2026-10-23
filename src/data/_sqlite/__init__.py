# src/data/_sqlite/__init__.py
"""SQLite 存储门面

- aiosqlite 驱动的仓储实现归属地
"""

from ._connection import close_all, get_connection
from ._factory import Repositories, build_repositories

__all__ = [
    # 连接
    "get_connection",
    "close_all",
    # 仓储装配
    "Repositories",
    "build_repositories",
]
