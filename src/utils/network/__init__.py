# src/utils/network/__init__.py
"""网络栈门面

- 代发 HTTP 客户端、链路状态、系统代理与探测协议键符号
- 底层实现分列 _client/_link/_proxy/probe，平台无关的校验编排在 utils.check
- 引擎侧的会话类归 Telegram 适配层，本门面不引 aiogram
"""

from ._client import BaseClient
from ._link import LinkStatus, link_report
from ._proxy import detect_system_proxy
from .probe import (
    Channel,
    FrameKey,
    RowId,
    RowStatus,
    plan_channels,
    sys_deduped,
    verify_plan,
    verify_skeleton,
    via_label,
)

__all__ = [
    # HTTP 客户端
    "BaseClient",
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
    # 探测规划
    "plan_channels",
    "sys_deduped",
    "via_label",
    "verify_plan",
    "verify_skeleton",
]
