# src/utils/check/__init__.py
"""连通检查门面

- 代发通道探测、并发调度、网络诊断与版本检查符号
- 底层网络栈在 utils.network，编排实现分列 _connectivity/_verify/_diagnose/_version
"""

from ._connectivity import attempt_channel, preload_engine
from ._diagnose import diagnose_flow
from ._verify import ChannelOutcome, local_row, run_channels
from ._version import check_updates

__all__ = [
    # 单通道探测
    "attempt_channel",
    "preload_engine",
    # 并行调度核心
    "run_channels",
    "local_row",
    "ChannelOutcome",
    # 网络诊断
    "diagnose_flow",
    # 版本检查
    "check_updates",
]
