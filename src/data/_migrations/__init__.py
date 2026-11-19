"""数据库迁移门面

- 代发结构版本号与迁移入口
"""

from ._runner import (
    SUPPORTED_SCHEMA,
    check_schema_compatible,
    purge_dead_tasks,
    run_migrations,
)

__all__ = [
    # 版本对照
    "SUPPORTED_SCHEMA",
    "check_schema_compatible",
    # 迁移执行
    "run_migrations",
    "purge_dead_tasks",
]
