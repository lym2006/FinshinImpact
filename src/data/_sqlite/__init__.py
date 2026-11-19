"""SQLite 存储门面

- 代发连接入口与仓储装配
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
