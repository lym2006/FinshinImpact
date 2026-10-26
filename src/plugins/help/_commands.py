# src/plugins/help/_commands.py
"""帮助命令

- /help：查询帮助（图片渲染）
- /命令 -h：单命令帮助查询
- 未知命令与非法形态：私聊回执，群聊与频道静默无视
- 清单顺序即匹配优先级，回执判定排最前才压得住命令侧
"""

import asyncio

from aiogram.types import Message

from core.domain import ChatScope, CommandFlag, ContentKind, PluginRoute, PluginSpec
from core.dto import CommandDTO, OutboundPayloadDTO
from services.context import HandlerContext

from .._shared.messages import BotMessage
from ._services import (
    command_specs,
    generate_image,
    help_list,
    resolve_single_help,
)

# 内部常量配置
_HELP_MENU = "help"  # 帮助菜单命令名
_MAX_FLAGS = 1
_MAX_FLAGS_WITH_HELP = 2  # -h 之外还可带一个
_ARGS_ALLOWED = frozenset({"grant", "ungrant"})  # 认位置参数的命令，其余带字即算多余


def _is_stray(command: CommandDTO) -> bool:
    """判定命令带了清单没认的输入

    - 不带 -h 时只认一个 flag，带 -h 时可再带一个
    - 同一 flag 重复算多余
    - 命令行只认开关，名单里的命令才收位置参数
    """
    entry = command_specs.get(command.head)
    declared = entry.flags if entry is not None else ()
    allowed: tuple[str, ...] = (CommandFlag.HELP, *(flag for flag, _ in declared))
    flags = command.flags
    if len(set(flags)) != len(flags):
        return True
    if any(flag not in allowed for flag in flags):
        return True
    limit = _MAX_FLAGS_WITH_HELP if CommandFlag.HELP in flags else _MAX_FLAGS
    if len(flags) > limit:
        return True
    return bool(command.args) and command.head not in _ARGS_ALLOWED


async def _is_illegal_command(ctx: HandlerContext) -> bool:
    """判定这条命令要拦截回执

    - 私聊里形态非法、菜单外命令名与清单没认的输入都回执
    - 群聊与频道只吞掉菜单内命令的多余输入，命令侧拿不到
    """
    command = ctx.event.command
    listed = command.matched and command.head in help_list
    if ctx.event.scope != ChatScope.PRIVATE:
        return listed and _is_stray(command)
    return command.format_error or (
        command.matched and (not listed or _is_stray(command))
    )


async def _is_single_help(ctx: HandlerContext) -> bool:
    """判定单命令帮助请求

    - 命中菜单内命令名且 flags 里有 -h
    - 清单没认的输入不接管，群聊里连同回执一并静默
    """
    command = ctx.event.command
    listed = command.matched and command.head in help_list
    has_help = CommandFlag.HELP in command.flags
    return listed and has_help and not _is_stray(command)


async def _is_menu_request(ctx: HandlerContext) -> bool:
    """判定帮助菜单请求

    - 裸 /help，不带 flag 与参数
    """
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


async def _reject_command(raw: Message, ctx: HandlerContext) -> None:
    """拦截命令形态问题

    - 私聊回执，群聊与频道静默无视
    """
    if ctx.event.scope != ChatScope.PRIVATE:
        return
    await ctx.answer(_reject_text(ctx.event.command))


async def _show_single_help(raw: Message, ctx: HandlerContext) -> None:
    """发送单个命令的帮助说明"""
    await ctx.answer(resolve_single_help(ctx.event.command.head))


async def _show_menu(raw: Message, ctx: HandlerContext) -> None:
    """以图片形式发送帮助菜单"""
    # 渲染可能触发绘制，放线程池防卡事件循环
    path = await asyncio.to_thread(generate_image)
    await ctx.answer(OutboundPayloadDTO(kind=ContentKind.PHOTO, local_path=str(path)))


spec = PluginSpec(
    routes=(
        PluginRoute(_is_illegal_command, _reject_command),
        PluginRoute(_is_single_help, _show_single_help),
        PluginRoute(_is_menu_request, _show_menu),
    )
)
