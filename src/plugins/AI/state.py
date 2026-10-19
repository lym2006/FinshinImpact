# src/plugins/AI/state.py
"""并发状态（内部实现）

- 定义用户级并发锁与全局注册表
"""

from asyncio import Lock
from collections import defaultdict

# 用户级异步锁：defaultdict 对新用户自动建锁
user_locks: dict[str, Lock] = defaultdict(Lock)
