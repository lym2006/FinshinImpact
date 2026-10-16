# src/core/domain/_command.py
"""命令值对象

- 定义跨平台归一的命令 flag 词表
"""

from enum import StrEnum


class CommandFlag(StrEnum):
    """命令 flag

    - -h 全命令默认支持，不登记进清单
    - 命令自有 flag 写在 plugin.toml 的 help.commands.flags，带短横
    """

    HELP = "-h"
