# src/core/contracts/_plugin.py
"""插件能力契约

- 定义平台召唤插件时交代的能力
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from finshin_sdk.dto import PrincipalDTO


@dataclass(frozen=True, slots=True)
class CapabilityCall:
    """平台召唤插件时交代的东西

    - 要往外说话的件从这里拿，用不上的件忽略它
    - 只带「发给谁」与「说什么」，要发出去的内容由平台拼好
    """

    say: Callable[[PrincipalDTO, str], Awaitable[None]]
