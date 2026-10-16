# src/plugins/help/_help.py
"""帮助命令

- /help：查询帮助（图片渲染）
- /命令 -h：单命令帮助查询
- 未知命令与非法形态：拦截并提示
"""

import asyncio

from aiogram import Bot, Router
from aiogram.filters import Command, Filter
from aiogram.types import FSInputFile, Message

from core.dto import CommandDTO
from services import HandlerContext

from ..messages import BotMessage
from ._services import generate_image, help_list, resolve_single_help

router = Router()

# 内部常量配置
_HELP_FLAG = "-h"  # 单命令帮助查询参数


async def _addressed_here(command: CommandDTO, bot: Bot) -> bool:
    """判定命令是否发给本机器人

    - 无点名段一律算发给我
    - 带点名段须与本人用户名相等，点名其他机器人的一律静默
    """
    if not command.mention:
        return True
    me = await bot.me()
    return bool(me.username) and command.mention.casefold() == me.username.casefold()


class _CommandReject(Filter):
    """筛选需要回执的非法命令

    - 形态非法与菜单外的命令名都要回执
    - 点名其他机器人的命令由对应机器人处理
    """

    async def __call__(
        self,
        message: Message,
        bot: Bot,
        ctx: HandlerContext | None = None,
    ) -> bool:
        """判定是否接管"""
        if ctx is None:
            return False
        command = ctx.event.command
        broken = command.format_error or (
            command.matched and command.name not in help_list
        )
        return broken and await _addressed_here(command, bot)


class _KeywordFilter(Filter):
    """筛选单命令帮助请求

    - 命中菜单内命令名且参数带 -h
    """

    async def __call__(
        self,
        message: Message,
        bot: Bot,
        ctx: HandlerContext | None = None,
    ) -> bool:
        """判定是否接管"""
        if ctx is None:
            return False
        command = ctx.event.command
        listed = command.matched and command.name in help_list
        return (
            listed
            and _HELP_FLAG in command.args
            and await _addressed_here(command, bot)
        )


@router.message(_CommandReject())
async def command_check(message: Message, ctx: HandlerContext) -> None:
    """回执命令形态问题

    - 首位形参由 aiogram 按位置绑定，名字不可改
    """
    command = ctx.event.command
    text = (
        BotMessage.CMD_FORMAT_ERROR
        if command.format_error
        else BotMessage.CMD_NOT_FOUND
    )
    await ctx.answer(text)


@router.message(_KeywordFilter())
async def command_help(message: Message, ctx: HandlerContext) -> None:
    """发送单个命令的帮助说明

    - 首位形参由 aiogram 按位置绑定，名字不可改
    """
    await ctx.answer(resolve_single_help(ctx.event.command.name))


@router.message(Command("help"))
async def show_help_list(message: Message) -> None:
    """以图片形式发送帮助菜单"""
    # 渲染可能触发绘制，放线程池防卡事件循环
    path = await asyncio.to_thread(generate_image)
    await message.answer_photo(FSInputFile(str(path)))
