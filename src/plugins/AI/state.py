# src/plugins/AI/state.py
"""并发状态

- 定义容器级并发锁与全局注册表
"""

from asyncio import Lock
from collections import defaultdict

from core.domain.ids import SessionKey

# 容器级异步锁：defaultdict 对新容器自动建锁
session_locks: dict[SessionKey, Lock] = defaultdict(Lock)
