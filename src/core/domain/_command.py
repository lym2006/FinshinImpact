# src/core/domain/_command.py
"""命令值对象

- 定义跨平台归一的命令 flag 词表
- 定义分步输入的保留串词表
"""

from enum import StrEnum


class CommandFlag(StrEnum):
    """命令 flag

    - -h 全命令默认支持，不登记进清单
    - 命令自有 flag 写在 plugin.toml 的 help.commands.flags，带短横
    """

    HELP = "-h"


class StepInput(StrEnum):
    """分步输入的保留串

    - 挂在待输入流程上时先于业务取值判定
    """

    STOP = "-1"  # 中止当前流程
