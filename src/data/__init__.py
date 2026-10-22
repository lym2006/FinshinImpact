# src/data/__init__.py
"""数据层门面

- 代发迁移入口与仓储装配
"""

from ._migrations import (
    SUPPORTED_SCHEMA,
    check_schema_compatible,
    purge_dead_tasks,
    run_migrations,
)
from ._sqlite import Repositories, build_repositories, get_connection

__all__ = [
    # 迁移
    "SUPPORTED_SCHEMA",
    "run_migrations",
    "check_schema_compatible",
    "purge_dead_tasks",
    # 仓储装配
    "get_connection",
    "Repositories",
    "build_repositories",
]
