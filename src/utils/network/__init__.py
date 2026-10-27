# src/utils/network/__init__.py
"""网络栈门面

- 代发 HTTP 客户端、SSL 会话、链路状态、系统代理与探测协议键符号
- 底层实现分列 _client/_session/_link/probe/proxy，平台无关的校验编排在 utils.check
- 会话类继承 aiogram，经模块 __getattr__ 延迟代发，门面导入不拖引擎入场
"""

from typing import TYPE_CHECKING, Any

from ._client import BaseClient
from ._link import LinkStatus, link_report
from .probe import (
    Channel,
    FrameKey,
    RowId,
    RowStatus,
    plan_channels,
    scan_proxy_ports,
    sys_deduped,
    verify_plan,
    verify_skeleton,
    via_label,
)
from .proxy import detect_system_proxy

if TYPE_CHECKING:
    from ._session import SSLUnverifiedSession, is_link_failure

# 延迟代发的符号 → 所在实现模块
_LAZY = {"SSLUnverifiedSession": "_session", "is_link_failure": "_session"}

__all__ = [
    # HTTP 与会话
    "BaseClient",
    "SSLUnverifiedSession",
    "is_link_failure",
    # 链路状态
    "LinkStatus",
    "link_report",
    # 系统代理
    "detect_system_proxy",
    # 通道与协议键
    "Channel",
    "FrameKey",
    "RowId",
    "RowStatus",
    # 探测规划与端口扫描
    "plan_channels",
    "scan_proxy_ports",
    "sys_deduped",
    "via_label",
    "verify_plan",
    "verify_skeleton",
]


def __getattr__(name: str) -> Any:
    """首次触碰才加载重实现模块

    - PEP 562 模块级懒加载，静态符号走常规属性不受影响
    """
    if name in _LAZY:
        from importlib import import_module

        value = getattr(import_module(f".{_LAZY[name]}", __name__), name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
