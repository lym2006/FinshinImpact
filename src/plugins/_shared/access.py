# src/plugins/_shared/access.py
"""命令权限守卫

- 主人档取配置 owner，管理员档为 owner 与被授权用户
- 档位判定单源在这里，命令与对话门槛都走它
- 装饰器按档位拦住无权限的命令
"""

from collections.abc import Awaitable, Callable
from functools import wraps
from typing import ParamSpec, cast

from bot.error_guard import error_guard
from core.domain import CommandRole, ConfigKey, ConfigSection
from core.dto import PrincipalDTO
from services.context import HandlerContext
from utils import config_manager, get_logger

from .grants import is_admin
from .messages import BotMessage

_logger = get_logger("Plg.Access")

# 泛型类型变量（用于装饰器的类型推导）
P = ParamSpec("P")


@error_guard("主人配置读取", reraise=True)
def _owner_id() -> str:
    """取主人 id

    - 配置里的 owner 串去空白后交出
    """
    return config_manager.get(ConfigKey.OWNER.path(ConfigSection.CHORE), str).strip()


async def role_of(principal: PrincipalDTO) -> CommandRole:
    """判定用户权限档

    - 配置 owner 命中即主人档
    - 命中授权名单算管理员，其余为用户
    """
    if _owner_id() == principal.user:
        return CommandRole.OWNER
    if await is_admin(principal.user_key):
        return CommandRole.ADMIN
    return CommandRole.MEMBER


def require_role(
    limit: CommandRole,
) -> Callable[[Callable[P, Awaitable[None]]], Callable[P, Awaitable[None]]]:
    """权限守卫装饰器

    - 档位低于要求的直接答无权限，不进处理函数
    """

    def decorator(
        func: Callable[P, Awaitable[None]],
    ) -> Callable[P, Awaitable[None]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> None:
            ctx = cast(HandlerContext, kwargs["ctx"])
            if await role_of(ctx.event.principal) > limit:
                _logger.info(f"{ctx.event.principal.key} 无权执行命令")
                await ctx.answer(BotMessage.CMD_NO_PERMISSION)
                return
            await func(*args, **kwargs)

        return wrapper

    return decorator
