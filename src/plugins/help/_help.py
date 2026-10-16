# src/plugins/help/_help.py
"""帮助命令

- /help：查询帮助（图片渲染）
- /命令 -h：单命令帮助查询
- 未知命令与非法形态：私聊回执，群聊与频道静默吞掉
"""

import asyncio

from aiogram import Router
from aiogram.filters import Filter
from aiogram.types import FSInputFile, Message

from core.domain import ChatScope, CommandFlag
from core.dto import CommandDTO
from services import HandlerContext

from ..messages import BotMessage
from ._services import (
    command_specs,
    generate_image,
    help_list,
    resolve_single_help,
)

router = Router()

# 内部常量配置
_HELP_MENU = "help"  # 帮助菜单命令名
_MAX_FLAGS = 1
_MAX_FLAGS_WITH_HELP = 2  # -h 之外还可带一个


def _is_stray(command: CommandDTO) -> bool:
    """判定命令带了清单没认的输入

    - 不带 -h 时只认一个 flag，带 -h 时可再带一个
    - 同一 flag 重复算多余
    - 位置参数一律算多余，命令要的内容走事件字段
    """
    spec = command_specs.get(command.head)
    declared = spec.flags if spec is not None else ()
    allowed: tuple[str, ...] = (CommandFlag.HELP.value, *(flag for flag, _ in declared))
    flags = command.flags
    if len(set(flags)) != len(flags):
        return True
    if any(flag not in allowed for flag in flags):
        return True
    limit = _MAX_FLAGS_WITH_HELP if CommandFlag.HELP.value in flags else _MAX_FLAGS
    return len(flags) > limit or bool(command.args)


class _CommandReject(Filter):
    """筛选需要拦截的非法命令

    - 私聊里形态非法、菜单外命令名与清单没认的输入都回执
    - 群聊与频道只吞掉菜单内命令的多余输入，命令侧不再参与
    """

    async def __call__(
        self, message: Message, ctx: HandlerContext | None = None
    ) -> bool:
        """判定是否接管"""
        if ctx is None:
            return False
        command = ctx.event.command
        listed = command.matched and command.head in help_list
        if ctx.event.scope is not ChatScope.PRIVATE:
            return listed and _is_stray(command)
        return command.format_error or (
            command.matched and (not listed or _is_stray(command))
        )


class _KeywordFilter(Filter):
    """筛选单命令帮助请求

    - 命中菜单内命令名且 flags 里有 -h
    - 清单没认的输入不接管，群聊里连同回执一并静默
    """

    async def __call__(
        self, message: Message, ctx: HandlerContext | None = None
    ) -> bool:
        """判定是否接管"""
        if ctx is None:
            return False
        command = ctx.event.command
        listed = command.matched and command.head in help_list
        has_help = CommandFlag.HELP.value in command.flags
        return listed and has_help and not _is_stray(command)


class _MenuFilter(Filter):
    """筛选帮助菜单请求

    - 裸 /help，不带 flag 与参数
    """

    async def __call__(
        self, message: Message, ctx: HandlerContext | None = None
    ) -> bool:
        """判定是否接管"""
        if ctx is None:
            return False
        command = ctx.event.command
        return (
            command.matched
            and command.head == _HELP_MENU
            and not command.flags
            and not command.args
        )


def _reject_text(command: CommandDTO) -> str:
    """选定非法命令的回执文案"""
    if command.format_error or command.head in help_list:
        return BotMessage.CMD_FORMAT_ERROR
    return BotMessage.CMD_NOT_FOUND


@router.message(_CommandReject())
async def command_check(message: Message, ctx: HandlerContext) -> None:
    """拦截命令形态问题

    - 私聊回执，群聊与频道静默吞掉
    - 首位形参由 aiogram 按位置绑定，名字不可改
    """
    if ctx.event.scope is not ChatScope.PRIVATE:
        return
    await ctx.answer(_reject_text(ctx.event.command))


@router.message(_KeywordFilter())
async def command_help(message: Message, ctx: HandlerContext) -> None:
    """发送单个命令的帮助说明

    - 首位形参由 aiogram 按位置绑定，名字不可改
    """
    await ctx.answer(resolve_single_help(ctx.event.command.head))


@router.message(_MenuFilter())
async def show_help_list(message: Message) -> None:
    """以图片形式发送帮助菜单"""
    # 渲染可能触发绘制，放线程池防卡事件循环
    path = await asyncio.to_thread(generate_image)
    await message.answer_photo(FSInputFile(str(path)))
