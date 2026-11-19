"""连通检查门面

- 代发并发调度、诊断编排与版本比对符号
- 凭证探测与引擎预热归各平台适配层，本门面只交平台无关的件
"""

from ._diagnose import bind_diagnose, diagnose_flow
from ._verify import ChannelOutcome, local_row, run_probe_round
from ._version import ReleaseNote, check_latest, release_history

__all__ = [
    # 并行调度核心
    "run_probe_round",
    "local_row",
    "ChannelOutcome",
    # 诊断编排
    "bind_diagnose",
    "diagnose_flow",
    # 版本比对
    "check_latest",
    "release_history",
    "ReleaseNote",
]
