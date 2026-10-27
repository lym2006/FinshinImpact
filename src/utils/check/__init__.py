# src/utils/check/__init__.py
"""连通检查门面

- 代发并发调度与版本检查符号
- 通道探测与诊断流程归各平台适配层，本门面只交平台无关的调度核心
"""

from ._verify import ChannelOutcome, local_row, run_channels
from ._version import ReleaseNote, check_updates, release_history

__all__ = [
    # 并行调度核心
    "run_channels",
    "local_row",
    "ChannelOutcome",
    # 版本检查
    "check_updates",
    "release_history",
    "ReleaseNote",
]
