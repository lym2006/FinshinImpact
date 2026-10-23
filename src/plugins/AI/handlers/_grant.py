# src/plugins/AI/handlers/_grant.py
"""授权命令

- /grant：主人授权某个 id 使用管理命令
- /ungrant：主人撤销授权
"""

from aiogram import Router
from aiogram.types import Message

from core.domain import CommandRole
from core.domain.ids import KEY_SEP, UserKey
from core.dto import PrincipalDTO
from services.context import HandlerContext

from ...filters import CommandFilter
from ...messages import BotMessage
from ..core import add_admin, remove_admin, require_role

grant = Router()


def _target_key(principal: PrincipalDTO, raw_id: str) -> UserKey:
    """按发起者的平台拼出被授权用户的二段键"""
    return UserKey(f"{principal.platform}{KEY_SEP}{raw_id}")


def _first_arg(ctx: HandlerContext) -> str:
    """取命令的第一个参数

    - 缺参即空串，由调用方判用法
    """
    args = ctx.event.command.args
    return args[0] if args else ""


@grant.message(CommandFilter("grant"))
@require_role(CommandRole.OWNER)
async def add_grant(raw: Message, ctx: HandlerContext) -> None:
    """授权用户"""
    raw_id = _first_arg(ctx)
    if not raw_id:
        await ctx.answer(BotMessage.GRANT_USAGE)
        return

    key = _target_key(ctx.event.principal, raw_id)
    added = await add_admin(key, ctx.event.principal.key)
    text = BotMessage.GRANT_ADDED if added else BotMessage.GRANT_EXISTS
    await ctx.answer(text.format(id=raw_id))


@grant.message(CommandFilter("ungrant"))
@require_role(CommandRole.OWNER)
async def drop_grant(raw: Message, ctx: HandlerContext) -> None:
    """撤销授权"""
    raw_id = _first_arg(ctx)
    if not raw_id:
        await ctx.answer(BotMessage.UNGRANT_USAGE)
        return

    removed = await remove_admin(_target_key(ctx.event.principal, raw_id))
    text = BotMessage.UNGRANT_REMOVED if removed else BotMessage.UNGRANT_MISSING
    await ctx.answer(text.format(id=raw_id))
