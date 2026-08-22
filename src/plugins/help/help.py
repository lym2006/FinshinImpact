# src/plugins/help/help.py
"""
帮助指令路由层

提供：
- /help 命令查询帮助，图文渲染
- 单命令帮助查询
- 未知命令拦截
"""

from aiogram import Router
from aiogram.filters import Command, Filter
from aiogram.types import FSInputFile, Message

from .services import generate_image, help_list, resolve_single_help

router = Router()

# ==================== 常量配置 ====================
HELP_FLAG = "-h"  # 单命令帮助查询参数
COMMAND_PREFIX = "/"  # 命令前缀


# ==================== 1. 内部辅助函数 ====================
def _is_command(text: str | None) -> bool:
    """判断消息是否为命令"""
    return text is not None and text.startswith(COMMAND_PREFIX)


def _get_words(message: Message) -> list[str]:
    """拆分消息文本"""
    text = message.text
    if not _is_command(text) or text is None:
        return []

    return text[1:].split()


# ==================== 2. 自定义过滤器 ====================
class StartWithSlash(Filter):
    """匹配 / 开头的未知命令"""

    async def __call__(self, message: Message) -> bool:
        """如果消息以 / 开头且不在已知命令列表中，返回 True"""
        words = _get_words(message)
        return len(words) != 0 and not any(w in help_list for w in words)


class KeywordFilter(Filter):
    """匹配 /命令 -h 格式（查看单个命令帮助）"""

    async def __call__(self, message: Message) -> bool:
        """如果消息包含 -h 参数且命令存在于已知列表中，返回 True"""
        words = _get_words(message)
        return (HELP_FLAG in words) and any(w in help_list for w in words)


# ==================== 3. 未知命令提示路由处理函数 ====================
@router.message(StartWithSlash())
async def command_check(message: Message) -> None:
    """检查未知命令并提示使用 /help"""
    text = message.text
    if text is None:
        return
    cmd = text.replace(" ", "").replace(COMMAND_PREFIX, "")
    if cmd not in help_list:
        await message.answer("命令不存在，请使用 /help ")


# ==================== 4. 单命令帮助路由处理函数 ====================
@router.message(KeywordFilter())
async def command_help(message: Message) -> None:
    """发送单个命令的帮助说明"""
    text = message.text
    if text is None:
        await message.answer("格式错误")
        return

    result = resolve_single_help(text)
    await message.answer(result)


# ==================== 5. /help 帮助查询命令 ====================
@router.message(Command("help"))
async def show_help_list(message: Message) -> None:
    """以图片形式发送帮助菜单"""
    path = generate_image()
    await message.answer_photo(FSInputFile(str(path)))
