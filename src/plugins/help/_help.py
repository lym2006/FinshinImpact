# src/plugins/help/_help.py
"""帮助命令

- /help：查询帮助（图片渲染）
- /命令 -h：单命令帮助查询
- 未知命令：拦截并提示使用 /help
"""

import asyncio

from aiogram import Router
from aiogram.filters import Command, Filter
from aiogram.types import FSInputFile, Message

from ..messages import BotMessage
from ._services import generate_image, help_list, resolve_single_help

router = Router()

# 内部常量配置
_HELP_FLAG = "-h"  # 单命令帮助查询参数
_COMMAND_PREFIX = "/"  # 命令前缀


def _is_command(text: str | None) -> bool:
    """判断消息是否为命令"""
    return text is not None and text.startswith(_COMMAND_PREFIX)


def _get_words(message: Message) -> list[str]:
    """拆分消息文本"""
    text = message.text
    if not _is_command(text) or text is None:
        return []

    return text[1:].split()


class _StartWithSlash(Filter):
    """匹配 / 开头的未知命令"""

    async def __call__(self, message: Message) -> bool:
        """检测未知命令"""
        words = _get_words(message)
        return len(words) != 0 and not any(w in help_list for w in words)


class _KeywordFilter(Filter):
    """匹配单命令帮助格式"""

    async def __call__(self, message: Message) -> bool:
        """检测帮助请求"""
        words = _get_words(message)
        return (_HELP_FLAG in words) and any(w in help_list for w in words)


@router.message(_StartWithSlash())
async def command_check(message: Message) -> None:
    """检查未知命令并提示使用 /help"""
    text = message.text
    if text is None:
        return
    cmd = text.replace(" ", "").replace(_COMMAND_PREFIX, "")
    if cmd not in help_list:
        await message.answer(BotMessage.CMD_NOT_FOUND)


@router.message(_KeywordFilter())
async def command_help(message: Message) -> None:
    """发送单个命令的帮助说明"""
    text = message.text
    if text is None:
        await message.answer(BotMessage.CMD_FORMAT_ERROR)
        return

    result = resolve_single_help(text)
    await message.answer(result)


@router.message(Command("help"))
async def show_help_list(message: Message) -> None:
    """以图片形式发送帮助菜单

    - 渲染可能触发绘制，放线程池防卡事件循环
    """
    path = await asyncio.to_thread(generate_image)
    await message.answer_photo(FSInputFile(str(path)))
