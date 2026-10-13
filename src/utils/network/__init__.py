# src/utils/network/__init__.py
"""网络栈门面

- 代发 HTTP 客户端、SSL 会话、系统代理与探测协议键符号
- 底层实现分列 _client/_session/proxy/probe，校验与诊断编排在 utils.check
"""

from ._client import BaseClient
from ._session import SSLUnverifiedSession
from .probe import (
    Channel,
    FieldKey,
    FrameKey,
    RowId,
    RowStatus,
    plan_channels,
    scan_proxy_ports,
    verify_plan,
    verify_skeleton,
    via_label,
)
from .proxy import detect_system_proxy

__all__ = [
    # HTTP 与会话
    "BaseClient",
    "SSLUnverifiedSession",
    # 系统代理
    "detect_system_proxy",
    # 通道与协议键
    "Channel",
    "FieldKey",
    "FrameKey",
    "RowId",
    "RowStatus",
    # 探测规划与端口扫描
    "plan_channels",
    "scan_proxy_ports",
    "via_label",
    "verify_plan",
    "verify_skeleton",
]
