# src/bundled/help/_commands.py
"""帮助命令

- /help：查询帮助（图片渲染）
- /命令 -h：单命令帮助查询
- 菜单内命令带了清单没认的输入：私聊与群里都给用法，群里引用发起人那条消息
- 未知命令名与非法形态只在私聊回执，频道静默无视
- 清单顺序即匹配优先级，回执判定排最前才压得住命令侧
"""

import asyncio
import time

from finshin_sdk import HandlerContext, MessageRoute
from finshin_sdk.domain import (
    BoundCommand,
    ChatScope,
    CommandFlag,
    ContentKind,
    bind_command,
)
from finshin_sdk.dto import CommandDTO, OutboundPayloadDTO
from utils import get_logger

from .._shared.messages import BotMessage
from ._services import (
    command_specs,
    generate_image,
    help_list,
    resolve_single_help,
    resolve_usage_hint,
)

# 内部常量配置
_HELP_MENU = "help"  # 帮助菜单命令名
_MAX_FLAGS = 1
_MAX_FLAGS_WITH_HELP = 2  # -h 之外还可带一个
_MAX_ARGS = 1  # 清单登记过 args 的命令只收一个位置参数


_logger = get_logger("Plg.Help")


def _bind(command: CommandDTO) -> BoundCommand:
    """按清单声明把命令片段绑成开关与参数

    - 带值开关的名单取自这条命令的清单声明
    - 清单没登记的命令按全不带值处理
    """
    entry = command_specs.get(command.head)
    declared = entry.flags if entry is not None else ()
    value_flags = frozenset(flag.name for flag in declared if flag.value)
    return bind_command(command.pieces, value_flags)


def _is_stray(command: CommandDTO) -> bool:
    """判定命令带了清单没认的输入

    - 不带 -h 时只认一个开关，带 -h 时可再带一个
    - 清单没登记的开关名与重复的开关都算多余
    - 清单写了值名的开关没绑到值算多余
    - 位置参数最多一个，且只认清单登记过位置参数的命令
    """
    entry = command_specs.get(command.head)
    declared = entry.flags if entry is not None else ()
    takes_args = bool(entry and entry.args)
    value_names = frozenset(flag.name for flag in declared if flag.value)
    allowed = {CommandFlag.HELP, *(flag.name for flag in declared)}
    bound = _bind(command)
    names = [name for name, _ in bound.flags]
    if any(name not in allowed for name in names):
        return True
    if len(set(names)) != len(names):
        return True
    limit = _MAX_FLAGS_WITH_HELP if CommandFlag.HELP in names else _MAX_FLAGS
    if len(names) > limit:
        return True
    if any(name in value_names and not value for name, value in bound.flags):
        return True
    return len(bound.args) > (_MAX_ARGS if takes_args else 0)


async def _is_illegal_command(ctx: HandlerContext) -> bool:
    """判定这条命令要拦截回执

    - 私聊里形态非法、菜单外命令名与清单没认的输入都回执
    - 群聊与频道只接菜单内命令的多余输入，命令侧拿不到
    - 回执发给谁与发什么由拒绝那条路由决定
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

    - 命中菜单内命令名且片段里有 -h
    - 清单没认的输入不接管
    """
    command = ctx.event.command
    listed = command.matched and command.head in help_list
    has_help = CommandFlag.HELP in command.pieces
    return listed and has_help and not _is_stray(command)


async def _is_menu_request(ctx: HandlerContext) -> bool:
    """判定帮助菜单请求

    - 裸 /help，不带开关与参数
    """
    command = ctx.event.command
    return command.matched and command.head == _HELP_MENU and not command.pieces


def _reject_text(command: CommandDTO) -> str:
    """选定非法命令的回执文案

    - 菜单内的命令给出这条命令的用法
    - 形态非法只报格式错误，菜单外的名只报不存在
    """
    if command.head in help_list:
        return resolve_usage_hint(command.head)
    if command.format_error:
        return BotMessage.CMD_FORMAT_ERROR
    return BotMessage.CMD_NOT_FOUND


async def _reject_command(platform_raw: object, ctx: HandlerContext) -> None:
    """回绝写法不对的命令

    - 频道静默无视
    """
    if ctx.event.scope == ChatScope.UNKNOWN:
        return
    await ctx.respond(_reject_text(ctx.event.command))


async def _show_single_help(platform_raw: object, ctx: HandlerContext) -> None:
    """发送单个命令的帮助说明"""
    await ctx.respond(resolve_single_help(ctx.event.command.head))


async def _show_menu(platform_raw: object, ctx: HandlerContext) -> None:
    """以图片形式发送帮助菜单

    - 取图与上传分开计时
    """
    started = time.perf_counter()

    # 渲染可能触发绘制，放线程池防卡事件循环
    path = await asyncio.to_thread(generate_image)
    drawn = time.perf_counter()
    await ctx.respond(OutboundPayloadDTO(kind=ContentKind.PHOTO, local_path=str(path)))
    sent = time.perf_counter()
    _logger.debug(
        f"帮助图送出：取图 {(drawn - started) * 1000:.0f} 毫秒、"
        f"上传 {(sent - drawn) * 1000:.0f} 毫秒、图 {path.stat().st_size // 1024} KB"
    )


ROUTES = (
    MessageRoute(_is_illegal_command, _reject_command),
    MessageRoute(_is_single_help, _show_single_help),
    MessageRoute(_is_menu_request, _show_menu),
)
