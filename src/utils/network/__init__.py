"""网络栈门面

- 按属性惰性解析，取用哪个符号才 import 哪个子模块
- 代发 HTTP 客户端、GitHub 取数通道、链路状态、系统代理与探测协议键符号
- 底层实现分列子模块，与平台无关的校验编排在检查门面
"""

import importlib
from typing import TYPE_CHECKING

_SYMBOL_MODULES = {
    "BaseClient": "._client",
    "GitClient": "._github",
    "LinkStatus": "._link",
    "link_report": "._link",
    "detect_system_proxy": "._proxy",
    "PROXY_ITEM": "._probe",
    "NETWORK_ROWS": "._probe",
    "Channel": "._probe",
    "FrameKey": "._probe",
    "RowId": "._probe",
    "RowStatus": "._probe",
    "plan_channels": "._probe",
    "probe_budget": "._probe",
    "probe_skeleton": "._probe",
    "single_row_of": "._probe",
    "sys_deduped": "._probe",
    "uses_configured_proxy": "._probe",
    "uses_system_proxy": "._probe",
    "fault_row_of": "._probe",
    "via_label": "._probe",
    "verify_plan": "._probe",
    "verify_skeleton": "._probe",
}

__all__ = [
    # HTTP 客户端
    "BaseClient",
    "GitClient",
    # 链路状态
    "LinkStatus",
    "link_report",
    # 系统代理
    "detect_system_proxy",
    # 通道与协议键
    "PROXY_ITEM",
    "NETWORK_ROWS",
    "Channel",
    "FrameKey",
    "RowId",
    "RowStatus",
    # 探测规划
    "plan_channels",
    "probe_budget",
    "probe_skeleton",
    "single_row_of",
    "sys_deduped",
    "uses_configured_proxy",
    "uses_system_proxy",
    "fault_row_of",
    "via_label",
    "verify_plan",
    "verify_skeleton",
]

if TYPE_CHECKING:
    from ._client import BaseClient
    from ._github import GitClient
    from ._link import LinkStatus, link_report
    from ._probe import (
        NETWORK_ROWS,
        PROXY_ITEM,
        Channel,
        FrameKey,
        RowId,
        RowStatus,
        fault_row_of,
        plan_channels,
        probe_budget,
        probe_skeleton,
        single_row_of,
        sys_deduped,
        uses_configured_proxy,
        uses_system_proxy,
        verify_plan,
        verify_skeleton,
        via_label,
    )
    from ._proxy import detect_system_proxy


def __getattr__(name: str) -> object:
    module_path = _SYMBOL_MODULES.get(name)
    if module_path is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(module_path, __name__)
    return getattr(module, name)
