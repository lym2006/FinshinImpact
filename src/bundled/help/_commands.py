"""帮助命令

- /help：查询帮助（图片渲染）
- /命令 -h：单命令帮助查询
- 菜单内命令带了清单没认的输入：私聊与群里都给用法，群里引用发起人那条消息
- 未知命令名与非法形态只在私聊回执，频道静默无视
- 回执判定排最前，其后是单命令帮助与菜单
"""

import asyncio
import time

from finshin_sdk import HandlerContext, MessageRoute
from finshin_sdk.domain import (
    BindFailure,
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


_logger = get_logger("Plg.Help")


def _bind(command: CommandDTO) -> BoundCommand | BindFailure:
    """按清单声明绑定命令片段

    - 开关名与默认值都取自这条命令的清单声明
    - 菜单外的命令名没有声明表，一律算绑不进
    """
    entry = command_specs.get(command.head)
    if entry is None:
        return BindFailure(got=command.head)
    return bind_command(
        command.pieces,
        [(flag.name, flag.default) for flag in entry.flags],
        bool(entry.args),
    )


def _is_stray(command: CommandDTO) -> bool:
    """判定命令带了清单绑不进的输入

    - 开关没登记、同一开关重复、带值开关没吃到值、值类型不对都算绑不进
    - 位置参数出现在开关之后、或命令没登记参数还带了内容都算绑不进
    """
    return isinstance(_bind(command), BindFailure)


async def _is_illegal_command(ctx: HandlerContext) -> bool:
    """判定这条命令要拦截回执

    - 私聊里形态非法、菜单外命令名与清单没认的输入都回执
    - 群聊与频道只接菜单内命令的多余输入，命令侧拿不到
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
    - 菜单内命令的绑不进现场落调试日志，屏上只给用法
    """
    command = ctx.event.command
    if command.head in help_list:
        failure = _bind(command)
        if isinstance(failure, BindFailure):
            _logger.debug(
                f"{command.head} 绑不进：开关 {failure.flag} 收到 {failure.got}"
            )
    if ctx.event.scope == ChatScope.UNKNOWN:
        return
    await ctx.respond(_reject_text(command))


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
