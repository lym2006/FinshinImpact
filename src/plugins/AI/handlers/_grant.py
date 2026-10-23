# src/plugins/AI/handlers/_grant.py
"""授权命令

- /grant：主人授权某个 id 使用管理命令
- /ungrant：主人撤销授权
- 不带 id 时挂起待输入，下一条只认发起人自己发来的 id
"""

from enum import StrEnum

from aiogram import Router
from aiogram.filters import Filter
from aiogram.types import Message

from core.domain import CommandRole, StepInput
from core.domain.ids import KEY_SEP, PrincipalKey, UserKey
from core.dto import PrincipalDTO
from services.context import HandlerContext

from ...filters import CommandFilter
from ...messages import BotMessage
from ..core import add_admin, remove_admin, require_role

grant = Router()


class _GrantStep(StrEnum):
    """待输入流程要办的动作"""

    ADD = "add"
    DROP = "drop"


# 待输入的授权流程，键即发起人在本容器的身份
_pending: dict[PrincipalKey, _GrantStep] = {}


class _AwaitTarget(Filter):
    """认待输入流程发来的目标

    - 只认发起流程的那个人，命令与图片不接
    """

    async def __call__(self, raw: Message, ctx: HandlerContext | None = None) -> bool:
        """判定是否接管这条消息"""
        if ctx is None:
            return False
        event = ctx.event
        command = event.command
        if command.matched or command.format_error:
            return False
        if event.content.media or not event.content.text:
            return False
        return _pending.get(event.principal.key) is not None


def _target_key(principal: PrincipalDTO, raw_id: str) -> UserKey:
    """按发起者的平台拼出被授权用户的二段键"""
    return UserKey(f"{principal.platform}{KEY_SEP}{raw_id}")


def _is_id(text: str) -> bool:
    """判定输入是不是一条用户 id

    - 平台 id 是正整数
    """
    return text.isdigit() and int(text) > 0


async def _apply(ctx: HandlerContext, step: _GrantStep, raw_id: str) -> None:
    """落名单并回执"""
    principal = ctx.event.principal
    if step is _GrantStep.ADD:
        added = await add_admin(_target_key(principal, raw_id), principal.key)
        text = BotMessage.GRANT_ADDED if added else BotMessage.GRANT_EXISTS
    else:
        removed = await remove_admin(_target_key(principal, raw_id))
        text = BotMessage.UNGRANT_REMOVED if removed else BotMessage.UNGRANT_MISSING
    await ctx.answer(text.format(id=raw_id))


def _ask_target(ctx: HandlerContext, step: _GrantStep) -> str:
    """挂起待输入并交出提问文案"""
    _pending[ctx.event.principal.key] = step
    return (
        BotMessage.GRANT_ASK_TARGET
        if step is _GrantStep.ADD
        else BotMessage.UNGRANT_ASK_TARGET
    )


async def _take_command(ctx: HandlerContext, step: _GrantStep, usage: str) -> None:
    """按命令带的参数决定执行、提问还是报用法

    - 恰好一个参数即直接办完
    - 没带参数挂起待输入
    - 参数多于一个只报用法
    """
    args = ctx.event.command.args
    if len(args) == 1:
        await _apply(ctx, step, args[0])
        return
    if not args:
        await ctx.answer(_ask_target(ctx, step))
        return
    await ctx.answer(usage)


@grant.message(CommandFilter("grant"))
@require_role(CommandRole.OWNER)
async def add_grant(raw: Message, ctx: HandlerContext) -> None:
    """授权用户"""
    await _take_command(ctx, _GrantStep.ADD, BotMessage.GRANT_USAGE)


@grant.message(CommandFilter("ungrant"))
@require_role(CommandRole.OWNER)
async def drop_grant(raw: Message, ctx: HandlerContext) -> None:
    """撤销授权"""
    await _take_command(ctx, _GrantStep.DROP, BotMessage.UNGRANT_USAGE)


@grant.message(_AwaitTarget())
@require_role(CommandRole.OWNER)
async def finish_grant(raw: Message, ctx: HandlerContext) -> None:
    """按待输入流程认目标"""
    key = ctx.event.principal.key
    step = _pending[key]
    target = (ctx.event.content.text or "").strip()

    if target == StepInput.STOP:
        _pending.pop(key, None)
        await ctx.answer(BotMessage.GRANT_CANCELED)
        return
    if not _is_id(target):
        await ctx.answer(BotMessage.GRANT_BAD_TARGET)
        return

    _pending.pop(key, None)
    await _apply(ctx, step, target)
