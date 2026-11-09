# src/core/contracts/_plugin.py
"""插件契约

- 定义平台召唤插件时交代的能力
- 定义随包插件专用的内部入口基类
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from finshin_sdk.domain import BasePlugin, PluginTiming
from finshin_sdk.dto import PrincipalDTO


@dataclass(frozen=True, slots=True)
class CapabilityCall:
    """平台召唤插件时交代的东西

    - 要往外说话的件从这里拿，用不上的件忽略它
    - 只带「发给谁」与「说什么」，要发出去的内容由平台拼好
    """

    say: Callable[[PrincipalDTO, str], Awaitable[None]]


class BundledPlugin(BasePlugin):
    """随包插件的内部入口基类

    - 平台时机订阅只在这一层开放，随包件与本体同一个版本、动一起动
    - 外部插件交这一份不生效，装载侧只认随包树里的它
    """

    def timings(self) -> tuple[PluginTiming, ...]:
        """平台时刻的订阅清单"""
        return ()
