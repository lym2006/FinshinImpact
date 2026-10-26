# src/plugins/_shared/grants.py
"""命令授权落库

- 按用户在本平台的 id 读写管理员名单
- 仓储首次用时装配
"""

from core.contracts import GrantRepository
from core.domain.ids import PrincipalKey, UserId
from data import build_repositories, get_connection
from utils.paths import DB_FILE

_grant_repo: GrantRepository | None = None


async def _repo() -> GrantRepository:
    """取出授权仓储

    - 首次调用装配，之后每次走同一条连接
    """
    global _grant_repo
    if _grant_repo is None:
        conn = await get_connection(DB_FILE)
        _grant_repo = build_repositories(conn).grant
    return _grant_repo


async def is_admin(user: UserId) -> bool:
    """判定用户是否在管理员名单里"""
    return await (await _repo()).contains(user)


async def add_admin(user: UserId, granted_by: PrincipalKey) -> bool:
    """授权用户

    - 返回是否新增，已在名单里保持原值
    """
    return await (await _repo()).grant(user, granted_by)


async def remove_admin(user: UserId) -> bool:
    """撤销授权

    - 返回撤销前名单里有没有
    """
    return await (await _repo()).revoke(user)


async def list_admins() -> tuple[UserId, ...]:
    """列出未到期的授权，按授权先后升序"""
    return await (await _repo()).list_active()
