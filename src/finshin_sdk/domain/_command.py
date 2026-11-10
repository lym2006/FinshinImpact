# src/finshin_sdk/domain/_command.py
"""命令值对象

- 跨平台归一的命令 flag 词表
- 分步输入的保留串词表
- 按清单声明的带值开关把命令片段绑成开关与参数
"""

import re
from dataclasses import dataclass
from enum import StrEnum

# 开关名形状：短横起头、紧跟字母，其后可带字母数字与下划线短横
_FLAG_NAME_RE = re.compile(r"-[A-Za-z][A-Za-z0-9_-]*")


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


@dataclass(frozen=True, slots=True)
class BoundCommand:
    """绑定后的命令输入

    - 开关项每项是「开关 值」，不带值的开关值为空串
    - 参数项是没被开关认领的片段，顺序原样保留
    """

    flags: tuple[tuple[str, str], ...] = ()
    args: tuple[str, ...] = ()


def is_flag_name(token: str) -> bool:
    """判定这段文本是开关名

    - 清单里的开关名与命令里带的片段共用这一个形状
    """
    return _FLAG_NAME_RE.fullmatch(token) is not None


def bind_command(pieces: tuple[str, ...], value_flags: frozenset[str]) -> BoundCommand:
    """按带值开关名单绑定命令片段

    - 名单内的开关吃掉紧跟其后的一段作为值
    - 开关后面紧跟开关即判缺值，值为空串
    - 名单外的开关算不带值，其余片段按原顺序落参数项
    """
    flags: list[tuple[str, str]] = []
    args: list[str] = []
    index = 0
    while index < len(pieces):
        piece = pieces[index]
        if not is_flag_name(piece):
            args.append(piece)
            index += 1
            continue
        if piece not in value_flags:
            flags.append((piece, ""))
            index += 1
            continue
        value = ""
        if index + 1 < len(pieces) and not is_flag_name(pieces[index + 1]):
            value = pieces[index + 1]
        flags.append((piece, value))
        index += 1 + bool(value)
    return BoundCommand(flags=tuple(flags), args=tuple(args))
