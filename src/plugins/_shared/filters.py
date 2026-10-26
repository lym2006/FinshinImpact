# src/plugins/_shared/filters.py
"""命令谓词

- 按归一事件的命令头匹配路由
"""

from core.domain import CommandFlag
from core.dto import CommandDTO
from services.context import HandlerContext


def _has_help_flag(command: CommandDTO) -> bool:
    """判定命令带 -h"""
    return CommandFlag.HELP in command.flags


class CommandMatch:
    """命令头匹配

    - 只比命令头，命令额外认哪些开关看插件清单
    - 带 -h 一律让行给帮助插件
    """

    def __init__(self, name: str) -> None:
        self._name = name

    async def __call__(self, ctx: HandlerContext) -> bool:
        """判定命令是否命中"""
        command = ctx.event.command
        if not command.matched or command.head != self._name:
            return False
        return not _has_help_flag(command)
