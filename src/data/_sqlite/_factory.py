# src/data/_sqlite/_factory.py
"""仓储装配

- 在同一连接上组装五个仓储
"""

from dataclasses import dataclass

import aiosqlite

from core.contracts import (
    GrantRepository,
    MediaRepository,
    PrincipalRepository,
    SessionRepository,
    TaskRepository,
)

from ._grant import SqliteGrantRepository
from ._media import SqliteMediaRepository
from ._principal import SqlitePrincipalRepository
from ._session import SqliteSessionRepository
from ._task import SqliteTaskRepository


@dataclass(frozen=True, slots=True)
class Repositories:
    """同一连接下的仓储集合"""

    principal: PrincipalRepository
    session: SessionRepository
    task: TaskRepository
    media: MediaRepository
    grant: GrantRepository


def build_repositories(conn: aiosqlite.Connection) -> Repositories:
    """组装五个仓储实例"""
    return Repositories(
        principal=SqlitePrincipalRepository(conn),
        session=SqliteSessionRepository(conn),
        task=SqliteTaskRepository(conn),
        media=SqliteMediaRepository(conn),
        grant=SqliteGrantRepository(conn),
    )
