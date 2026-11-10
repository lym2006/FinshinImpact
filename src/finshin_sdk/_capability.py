# src/finshin_sdk/_capability.py
"""平台交代

- 定义召唤插件时交给它的那一份能力
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from .dto import PrincipalDTO


@dataclass(frozen=True, slots=True)
class CapabilityCall:
    """平台召唤插件时交代的东西

    - 要往外说话的件从这里拿
    - 只带「发给谁」与「说什么」，要发出去的内容由平台拼好
    """

    say: Callable[[PrincipalDTO, str], Awaitable[None]]
