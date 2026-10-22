# src/data/_migrations/__init__.py
"""数据库迁移门面

- Schema 版本管理与升降级脚本的归属地
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
