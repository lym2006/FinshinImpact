# src/bot/_adapter_host/_assemble.py
"""平台装配

- 取件、造运行时、挂日志中间件、按启用序列注册插件
"""

from finshin_sdk import PlatformAssembly
from finshin_sdk.domain import Platform
from utils.middleware import LoggingMiddleware
from utils.plugin import register_plugins

from ._parts import parts_for


def assemble_platform(
    platform: Platform, token: str, proxy: str | None
) -> PlatformAssembly:
    """装配一个平台的运行时与插件清单

    - 日志中间件与插件注册归本体，适配器只交出挂载口与清单编译器
    """
    adapter = parts_for(platform).assemble(token, proxy)
    adapter.attach_middleware(LoggingMiddleware())
    report, loops, actions, platform_moments = register_plugins(
        adapter.route_sink, adapter.router_builder
    )
    return PlatformAssembly(adapter, report, loops, actions, platform_moments)
